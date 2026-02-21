from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image
import io, time, os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from Chat import router as chat_router

app = FastAPI(title="Chest X-Ray Abnormality Detector", version="2.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")
app.include_router(chat_router)

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = str(BASE_DIR / "training" / "models" / "best.pt")

CLASS_NAMES = [
    "Aortic enlargement", "Atelectasis", "Calcification", "Cardiomegaly",
    "Consolidation", "ILD", "Infiltration", "Lung Opacity",
    "Nodule/Mass", "Other lesion", "Pleural effusion", "Pleural thickening",
    "Pneumothorax", "Pulmonary fibrosis",
]

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------- LOAD MODEL ----------------
print(f"Loading YOLO11 model from {MODEL_PATH}...")
model = YOLO(MODEL_PATH)
print(f"✅ Model loaded on {device} | {len(CLASS_NAMES)} classes")

# ---------------- HELPERS ----------------
def format_detections(results, conf_threshold=0.25):
    """Convert YOLO results to a clean JSON-serializable format."""
    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue

        img_h, img_w = result.orig_shape

        for i in range(len(boxes)):
            conf = float(boxes.conf[i])
            if conf < conf_threshold:
                continue

            cls_id = int(boxes.cls[i])
            x1, y1, x2, y2 = boxes.xyxy[i].tolist()

            detections.append({
                "class_id": cls_id,
                "class_name": CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}",
                "confidence": round(conf, 4),
                "bbox": {
                    "x_min": round(x1, 1),
                    "y_min": round(y1, 1),
                    "x_max": round(x2, 1),
                    "y_max": round(y2, 1),
                },
                "bbox_normalized": {
                    "x_min": round(x1 / img_w, 4),
                    "y_min": round(y1 / img_h, 4),
                    "x_max": round(x2 / img_w, 4),
                    "y_max": round(y2 / img_h, 4),
                },
            })

    # Sort by confidence (highest first)
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return detections

# ---------------- ROUTES ----------------
@app.get("/")
def root():
    return {"message": "Chest X-Ray Abnormality Detector API v2.0 (YOLO11)"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "device": device,
        "model_loaded": True,
        "model": "YOLO11m",
        "classes": CLASS_NAMES,
        "num_classes": len(CLASS_NAMES),
    }

@app.get("/model_info")
def model_info():
    return {
        "architecture": "YOLO11m",
        "framework": "Ultralytics + PyTorch",
        "task": "object_detection",
        "num_classes": len(CLASS_NAMES),
        "classes": CLASS_NAMES,
        "input_size": 640,
        "metrics": {
            "mAP50": 0.336,
            "mAP50-95": 0.168,
            "precision": 0.392,
            "recall": 0.356,
        },
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Detect abnormalities in a chest X-ray image.
    Returns bounding boxes, class labels, and confidence scores.
    """
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    start_time = time.time()
    results = model.predict(
        source=image,
        conf=0.25,
        iou=0.45,
        device=device,
        verbose=False,
    )
    inference_time = round(time.time() - start_time, 3)

    detections = format_detections(results)

    # Determine overall finding
    if detections:
        top_finding = detections[0]
        summary = f"{top_finding['class_name']} ({top_finding['confidence']:.1%} confidence)"
    else:
        summary = "No abnormalities detected"

    return {
        "filename": file.filename,
        "summary": summary,
        "num_detections": len(detections),
        "detections": detections,
        "model_used": "YOLO11m",
        "inference_time_seconds": inference_time,
        "image_size": {"width": image.width, "height": image.height},
    }

@app.post("/batch_predict")
async def batch_predict(files: list[UploadFile] = File(...)):
    """Detect abnormalities in multiple chest X-ray images."""
    results_list = []
    total_start = time.time()

    for file in files:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        start_time = time.time()
        results = model.predict(
            source=image,
            conf=0.25,
            iou=0.45,
            device=device,
            verbose=False,
        )
        inference_time = round(time.time() - start_time, 3)

        detections = format_detections(results)

        results_list.append({
            "filename": file.filename,
            "num_detections": len(detections),
            "detections": detections,
            "inference_time_seconds": inference_time,
            "image_size": {"width": image.width, "height": image.height},
        })

    total_time = round(time.time() - total_start, 3)

    return {
        "total_images": len(results_list),
        "total_time_seconds": total_time,
        "results": results_list,
    }
