from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from transformers import AutoProcessor, AutoModel
from PIL import Image
import torch
import io
import json
import asyncio
import uvicorn

app = FastAPI()

# SECURITY: Prevent server overload
gpu_lock = asyncio.Lock()

print("Loading MedSigLIP...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "google/medsiglip-448"

processor = AutoProcessor.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id).to(device)
print("MedSigLIP Loaded!")

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), concerns: str = Form(...)):
    # 1. Parse Input
    try:
        labels = json.loads(concerns)
    except:
        raise HTTPException(400, "Invalid JSON")

    # 2. Process Image
    content = await file.read()
    image = Image.open(io.BytesIO(content)).convert("RGB")

    # 3. GPU Inference (Protected by Lock)
    # This ensures only 1 request hits the GPU at a time
    async with gpu_lock:
        with torch.inference_mode():
            inputs = processor(
                text=labels, 
                images=image, 
                padding="max_length", 
                truncation=True, 
                max_length=64, 
                return_tensors="pt"
            ).to(device)

            outputs = model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1).cpu().numpy()[0]

    # 4. Format Output
    return {label: float(probs[i]) for i, label in enumerate(labels)}

if __name__ == "__main__":
    # Workers MUST be 1. Do not increase this.
    uvicorn.run(app, host="127.0.0.1", port=9000, workers=1)