import torch
import cv2
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Verify Torch
print(f"Torch version: {torch.__version__}")
assert torch.cuda.is_available(), "CUDA not available. Check GPU setup."

# Verify OpenCV
print(f"OpenCV version: {cv2.__version__}")

# Verify GStreamer
Gst.init(None)
print("GStreamer initialized successfully.")
