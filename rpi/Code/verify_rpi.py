import sounddevice as sd
import vosk
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Verify Vosk
print(f"Vosk version: {vosk.__version__}")

# Verify SoundDevice
print(f"Available audio devices: {sd.query_devices()}")

# Verify GStreamer
Gst.init(None)
print("GStreamer initialized successfully.")
