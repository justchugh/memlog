from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import gradio as gr
import torch
import numpy as np

# Load Model
model_id = "vikhyatk/moondream2"
revision = "2024-07-23"
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    revision=revision,
    torch_dtype=torch.float16
).to("cuda")

tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)

# Webcam Input Function
def process_webcam_frame(image):
    if image is None:
        return "No image provided."
    # Convert to PIL Image if it's not already
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image.astype('uint8'), 'RGB')
    enc_image = model.encode_image(image)
    response = model.answer_question(enc_image, "Describe this image, and tell what all things do you see", tokenizer)
    return response

# Setup Gradio Interface without 'source' parameter
interface = gr.Interface(
    fn=process_webcam_frame,
    inputs=gr.Image(label="Webcam Feed", type="numpy"),
    outputs="text",
    live=True
)

# Launch Interface
interface.launch()
