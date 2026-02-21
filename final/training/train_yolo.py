"""
YOLO11 Training Script for Chest X-ray Abnormality Detection

Trains a YOLO11m model (latest Ultralytics, best accuracy)
on the VinBigData-derived YOLO dataset with optimized
hyperparameters for medical imaging.

Features:
  - Auto-resume: if a previous run exists, resumes from last checkpoint
  - Graceful stop: press Ctrl+C to stop training — results are saved automatically
  - GPU auto-detection with adaptive batch size
"""

from ultralytics import YOLO
from pathlib import Path
import torch
import os
import sys
import signal
import pandas as pd
import shutil
import json
import time


def train():
    # ---- Config ----
    BASE = Path(__file__).resolve().parent
    DATA_YAML = str(BASE / "yolo_dataset" / "dataset.yaml")
    PROJECT = str(BASE / "runs")
    NAME = "active_run"
    # Path for the centralized best model and metrics
    MODELS_DIR = BASE / "models"
    MODELS_DIR.mkdir(exist_ok=True)
    GLOBAL_BEST_WEIGHTS = MODELS_DIR / "best.pt"
    METRICS_JSON = MODELS_DIR / "best_metrics.json"

    # Check for resume in the single consolidated folder
    last_weights = Path(PROJECT) / NAME / "weights" / "last.pt"
    resume_mode = last_weights.exists()
    current_run_name = NAME

    # Device
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"🔧 Device: {'CUDA (GPU)' if device == '0' else 'CPU'}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"   VRAM: {vram_gb:.1f} GB")

    # Adapt batch size to VRAM
    # if torch.cuda.is_available():
    #     vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    #     if vram >= 16:
    #         batch_size = 16
    #     elif vram >= 8:
    #         batch_size = 8
    #     else:
    #         batch_size = 4
    # else:
    #     batch_size = 4

    print(f"   Batch size: {8}")
    print(f"   Model: YOLO11m (latest, best accuracy)")

    if resume_mode:
        # ---- Resume from last checkpoint ----
        print(f"\n🔄 RESUMING from: {last_weights}")
        print("   (Previous training was stopped — continuing where you left off)")
        model = YOLO(str(last_weights))
        try:
            results = model.train(resume=True)
        except (AssertionError, Exception) as e:
            if "nothing to resume" in str(e) or "is finished" in str(e):
                # Previous training completed all epochs — start fresh with best weights
                best_weights = Path(PROJECT) / NAME / "weights" / "best.pt"
                if best_weights.exists():
                    print(f"\n⚠️  Previous training completed all epochs.")
                    print(f"   Starting NEW training using best weights: {best_weights}")
                    model = YOLO(str(best_weights))
                    results = model.train(
                        data=DATA_YAML,
                        epochs=50,
                        batch=8,
                        imgsz=640,
                        device=device,
                        project=PROJECT,
                        name=NAME,
                        exist_ok=True,
                        optimizer="AdamW",
                        lr0=0.0005,       # Lower LR since we're fine-tuning
                        lrf=0.01,
                        weight_decay=0.0005,
                        warmup_epochs=3,
                        warmup_momentum=0.8,
                        augment=True,
                        hsv_h=0.01,
                        hsv_s=0.2,
                        hsv_v=0.3,
                        degrees=10,
                        translate=0.1,
                        scale=0.3,
                        flipud=0.3,
                        fliplr=0.5,
                        mosaic=0.8,
                        mixup=0.1,
                        patience=10,
                        save=True,
                        val=True,
                        plots=True,
                        workers=4,
                        amp=True,
                        cache=False,
                        verbose=True,
                    )
                else:
                    raise
            else:
                raise
    else:
        if GLOBAL_BEST_WEIGHTS.exists():
            print(f"\n🌟 Initializing NEW run using GLOBAL best weights: {GLOBAL_BEST_WEIGHTS}")
            model = YOLO(str(GLOBAL_BEST_WEIGHTS))
        else:
            # Fallback to v2 best if global best doesn't exist yet
            v2_path = Path(PROJECT) / "chest_xray_yolo11_v2"
            v2_best = v2_path / "weights" / "best.pt"
            if v2_best.exists():
                print(f"\n📦 Initializing NEW run using v2 best weights: {v2_best}")
                model = YOLO(str(v2_best))
                # Seed metrics from v2 if they don't exist
                if not METRICS_JSON.exists():
                    def get_map_from_v2(path):
                        csv_path = Path(path) / "results.csv"
                        if not csv_path.exists(): return 0.0
                        try:
                            df = pd.read_csv(csv_path)
                            mc = [c for c in df.columns if "metrics/mAP50(B)" in c]
                            return df[mc[0]].max() if mc else 0.0
                        except: return 0.0
                    
                    m = get_map_from_v2(v2_path)
                    with open(METRICS_JSON, "w") as f:
                        json.dump({"best_mAP50": float(m), "run_dir": "v2_fallback"}, f)
                    print(f"📈 Seeded benchmark: {m:.4f} mAP50")
                print(f"📈 Seeded benchmark: {m:.4f} mAP50")
            else:
                # Use absolute path to project root for weights to prevent redownloading in training/ folder
                ROOT_WEIGHTS = BASE.parent / "yolo11m.pt"
                print(f"\n📦 Loading YOLO11m from project root: {ROOT_WEIGHTS}")
                model = YOLO(str(ROOT_WEIGHTS))

        # Callback for real-time best model update
        def on_train_epoch_end(trainer):
            """Compare current best mAP against global record after each epoch."""
            try:
                # Load current benchmark
                current_benchmark = 0.0
                if METRICS_JSON.exists():
                    with open(METRICS_JSON, "r") as f:
                        data = json.load(f)
                        current_benchmark = data.get("best_mAP50", 0.0)

                # Get current best mAP from the trainer
                # trainer.metrics is a dict, keys include 'metrics/mAP50(B)'
                if hasattr(trainer, 'metrics'):
                    current_run_best = trainer.metrics.get('metrics/mAP50(B)', 0.0)
                    
                    if current_run_best > current_benchmark:
                        # Copy the best weights from this run to the global models dir
                        run_best_weights = Path(trainer.save_dir) / 'weights' / 'best.pt'
                        if run_best_weights.exists():
                            shutil.copy2(str(run_best_weights), str(GLOBAL_BEST_WEIGHTS))
                            # Update metrics JSON
                            new_metrics = {
                                "best_mAP50": float(current_run_best),
                                "run_dir": str(trainer.save_dir),
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            with open(METRICS_JSON, "w") as f:
                                json.dump(new_metrics, f, indent=4)
                            print(f"\n🌟 REAL-TIME GLOBAL BEST! Acc: {current_run_best:.4f} | Saved to: {GLOBAL_BEST_WEIGHTS}")
            except Exception as e:
                print(f"⚠️ Callback error: {e}")

        # Add the callback to the model
        model.add_callback("on_train_epoch_end", on_train_epoch_end)

        print(f"\n🚀 Starting training on {DATA_YAML}")
        print(f"   Project: {PROJECT}")
        print(f"   Run name: {NAME}")
        print(f"   Workers: 2 (Safe mode to prevent MemoryError)")
        print(f"\n💡 TIP: Press Ctrl+C at any time to stop training.")
        print(f"   Results will be saved. Re-run this script to resume.\n")

        results = model.train(
            data=DATA_YAML,
            epochs=50,
            batch=8,
            imgsz=640,
            device=device,
            project=PROJECT,
            name=NAME,
            exist_ok=True,

            # Optimizer & LR
            optimizer="AdamW",
            lr0=0.001,
            lrf=0.01,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,

            # Augmentation (tuned for medical imaging)
            augment=True,
            hsv_h=0.01,
            hsv_s=0.2,
            hsv_v=0.3,
            degrees=10,
            translate=0.1,
            scale=0.3,
            flipud=0.3,
            fliplr=0.5,
            mosaic=0.8,
            mixup=0.1,

            # Training params
            patience=5,
            save=True,
            val=True,
            plots=True,

            # Performance
            workers=2,        # REDUCED from 8 to 2 to fix MemoryError
            amp=True,
            cache=False,

            # Logging
            verbose=True,
        )

    return results


if __name__ == "__main__":
    train()
