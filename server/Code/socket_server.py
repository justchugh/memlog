import os
import time
import gi
import cv2
import numpy as np
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import torch
import warnings
import socket
import threading

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning)

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

# Output CSV file
output_file = "path/to/location/captions_output.csv" # Add path to store output


#os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use "0" if you want the first GPU

# Load Model
model_id = "vikhyatk/moondream2"
revision = "2024-07-23"

device = torch.device("cuda")  # Change to GPU
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    revision=revision,
    torch_dtype=torch.float16  # Use float16 for GPU
).to(device)

model.eval()
tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)

# Initialize audio transcription storage
audio_transcription = ""

# Audio server function to receive transcriptions
def audio_server():
    global audio_transcription
    host = '0.0.0.0'  # Listen on all interfaces
    port = 5001       # Port that matches the client's configuration

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((host, port))
        server_sock.listen(1)
        print("Waiting for connection...")

        conn, addr = server_sock.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                # Update audio transcription
                audio_transcription = data.decode('utf-8').strip()
                print(f"Audio transcription received: {audio_transcription}")

# Start audio server in a separate thread
threading.Thread(target=audio_server, daemon=True).start()

def on_new_sample(sink, data):
    """
    Callback function triggered when a new sample is available from appsink.
    """

    # Skip processing if a frame is already being processed
    if on_new_sample.is_processing:
        return Gst.FlowReturn.OK
    on_new_sample.is_processing = True

    sample = sink.emit('pull-sample')
    if not sample:
        print("Failed to pull sample from pipeline.")
        on_new_sample.is_processing = False
        return Gst.FlowReturn.ERROR

    buf = sample.get_buffer()
    caps = sample.get_caps()
    structure = caps.get_structure(0)
    width = structure.get_value('width')
    height = structure.get_value('height')
    format_str = structure.get_value('format')

    success, map_info = buf.map(Gst.MapFlags.READ)
    if not success:
        print("Failed to map buffer data.")
        on_new_sample.is_processing = False
        return Gst.FlowReturn.ERROR

    global audio_transcription

    try:
        # Extract raw frame data
        frame_data = map_info.data

        # Convert raw data to NumPy array
        frame = np.frombuffer(frame_data, np.uint8).reshape((height, width, 3))

        # Implement frame rate control: process one frame per second
        current_time = time.time()
        if not hasattr(on_new_sample, "last_processed"):
            on_new_sample.last_processed = 0

        if current_time - on_new_sample.last_processed >= 1:
            on_new_sample.last_processed = current_time

            # Convert frame to PIL Image
            image = Image.fromarray(frame[..., ::-1])  # Convert BGR to RGB

            # Start timing
            start_time = time.time()

            # Process image and generate caption
            try:
                # Ensure image is in the correct device
                enc_image = model.encode_image(image).to(device)
                response = model.answer_question(enc_image, "Describe this image.", tokenizer)
            except Exception as e:
                print(f"Failed to process frame: {e}")
                response = "Error generating caption."

            end_time = time.time()
            processing_time = round(end_time - start_time, 4)

            # Get timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Prepare caption and audio transcription for CSV output
            caption = response.replace(',', ' ')
            audio_text = audio_transcription.replace(',', ' ')  # Ensure no commas in audio text
            output_line = f'{timestamp},"{caption}",{processing_time},"{audio_text}"\n'

            # Write to output CSV file
            with open(output_file, 'a') as f_out:
                f_out.write(output_line)

            # Clear audio transcription after saving
            audio_transcription = ""

            print(f"Processed frame at {timestamp}: {caption} ({processing_time}s) | Audio: {audio_text}")

    except Exception as e:
        print(f"Error processing frame: {e}")
    
    finally:
        # Ensure the flag is reset, regardless of success or error
        on_new_sample.is_processing = False
        buf.unmap(map_info)

    return Gst.FlowReturn.OK


# Initialize the processing flag after defining the function
on_new_sample.is_processing = False

def main():
    # Open the output file in write mode and write header
    with open(output_file, 'w') as f_out:
        f_out.write("timestamp,caption,processing_time_seconds,audio_transcription\n")

    # GStreamer pipeline for receiving the stream
    pipeline_description = (
        'udpsrc port=5000 caps="application/x-rtp, media=video, encoding-name=H264, payload=96" ! '
        'rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw, format=BGR ! appsink name=sink emit-signals=True sync=False'
    )

    print(f"Using GStreamer pipeline: {pipeline_description}")

    # Parse the pipeline
    pipeline = Gst.parse_launch(pipeline_description)

    # Get the appsink element
    appsink = pipeline.get_by_name('sink')
    if not appsink:
        print("Error: Could not find 'sink' in pipeline.")
        exit(1)

    # Set appsink properties
    appsink.set_property("emit-signals", True)
    appsink.set_property("sync", False)

    # Connect the callback for new samples
    appsink.connect("new-sample", on_new_sample, None)

    # Start the pipeline
    pipeline.set_state(Gst.State.PLAYING)

    # Create and run the main loop
    loop = GLib.MainLoop()

    try:
        print("Starting main loop. Press Ctrl+C to stop.")
        loop.run()
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up GStreamer pipeline
        pipeline.set_state(Gst.State.NULL)
        print("GStreamer pipeline stopped.")

if __name__ == "__main__":
    main()
