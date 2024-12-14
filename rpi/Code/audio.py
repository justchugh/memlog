import sounddevice as sd
import vosk
import queue
import json
import datetime
import socket

# Set up the Vosk model
model = vosk.Model("model/us_eng")
samplerate = 16000  # Sample rate expected by the model

# Create a queue to hold audio data
q = queue.Queue()

# Socket setup
host = "server's IP address"  # Laptop IP, like 192.168.1.42
port = 5001  # Port to send transcriptions
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# Callback function to capture audio data
def callback(indata, frames, time, status):
    q.put(bytes(indata))

# Start streaming transcriptions
try:
    # Set up the recognizer
    rec = vosk.KaldiRecognizer(model, samplerate)
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        print("Listening and streaming transcriptions...")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = rec.Result()
                text = json.loads(result).get("text", "")
                if text:
                    # Create timestamped message
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    message = f"[{timestamp}] {text}\n"
                    print(message)

                    # Send the message over the network
                    sock.sendall(message.encode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
finally:
    sock.close()
