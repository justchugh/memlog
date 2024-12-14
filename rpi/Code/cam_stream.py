import subprocess
import curses
import time
import os
import signal

# Function to find and kill any process using the camera (/dev/video0)
def kill_camera_process():
    try:
        # Find the PID of the process using /dev/video0
        result = subprocess.run(['lsof', '/dev/video0'], capture_output=True, text=True)
        
        # Check if there's any process using the camera
        if result.stdout:
            # Extract the PID (process ID)
            lines = result.stdout.splitlines()
            for line in lines:
                if '/dev/video0' in line:
                    pid = int(line.split()[1])
                    print(f"Killing process {pid} that is using the camera.")
                    
                    # Kill the process
                    os.kill(pid, signal.SIGKILL)  # Force kill (SIGKILL)
                    
    except Exception as e:
        print(f"Error in killing camera process: {e}")

# Function to start the GStreamer pipeline
def start_streaming():
    # Command to start the GStreamer pipeline
    gst_command = [
        "gst-launch-1.0",
        "v4l2src", "device=/dev/video0",
        "!", "videoconvert",
        "!", "x264enc", "tune=zerolatency", "bitrate=300", "speed-preset=superfast",
        "!", "rtph264pay",
        "!", "udpsink", "host=server's IP address", "port=5000" #Add server's IP address, like 192.168.1.42
    ]

    try:
        # Start the GStreamer process
        process = subprocess.Popen(gst_command)
        print("Streaming started...")
        return process
    except FileNotFoundError:
        print("Error: GStreamer (gst-launch-1.0) not found. Ensure it is installed.")
    except Exception as e:
        print(f"Error starting the streaming process: {e}")

# Function to stop streaming on 'q' press using curses
def stop_streaming(stdscr, process):
    stdscr.nodelay(True)  # Make getch() non-blocking
    stdscr.clear()
    stdscr.addstr(0, 0, "Press 'q' to stop streaming...")

    while True:
        key = stdscr.getch()
        if key == ord('q'):
            stdscr.addstr(1, 0, "Stopping the stream...")
            stdscr.refresh()
            if process:
                process.terminate()  # Stop the GStreamer process
                process.wait()  # Wait for the process to exit
            break
        time.sleep(0.1)

# Main function to control streaming and stopping
def main():
    # Kill any process that is using the camera
    kill_camera_process()
    
    # Start streaming
    process = start_streaming()

    # Initialize curses for non-blocking key detection
    if process:
        curses.wrapper(stop_streaming, process)
    else:
        print("Streaming could not start due to an error.")

# Entry point of the script
if __name__ == "__main__":
    main()
