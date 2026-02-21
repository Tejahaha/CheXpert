"""
Convert VinBigData Chest X-ray CSV annotations → YOLO format.

Steps:
1. Parse train.csv
2. Aggregate multi-radiologist boxes via Weighted Boxes Fusion (WBF)
3. Convert to YOLO format (class x_center y_center width height, normalized 0-1)
4. Split into train/val (85/15)
5. Create YOLO directory structure with symlinks
6. Create dataset.yaml
"""

import os
import sys
import shutil
import random
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from PIL import Image

# ============================================================
# Weighted Boxes Fusion (simplified inline implementation)
# ============================================================
def weighted_boxes_fusion(boxes_list, scores_list, labels_list, iou_thr=0.5, skip_box_thr=0.0):
    """
    Simplified Weighted Boxes Fusion for merging multi-annotator boxes.
    boxes_list: list of arrays, each [N, 4] with (x1, y1, x2, y2) normalized 0-1
    scores_list: list of arrays, each [N]
    labels_list: list of arrays, each [N]
    Returns: merged (boxes, scores, labels)
    """
    if len(boxes_list) == 0:
        return np.empty((0, 4)), np.empty(0), np.empty(0)

    # Flatten all boxes
    all_boxes = []
    all_scores = []
    all_labels = []
    for boxes, scores, labels in zip(boxes_list, scores_list, labels_list):
        for b, s, l in zip(boxes, scores, labels):
            if s > skip_box_thr:
                all_boxes.append(b)
                all_scores.append(s)
                all_labels.append(l)

    if len(all_boxes) == 0:
        return np.empty((0, 4)), np.empty(0), np.empty(0)

    all_boxes = np.array(all_boxes)
    all_scores = np.array(all_scores)
    all_labels = np.array(all_labels)

    # Group by label
    unique_labels = np.unique(all_labels)
    final_boxes = []
    final_scores = []
    final_labels = []

    for label in unique_labels:
        mask = all_labels == label
        label_boxes = all_boxes[mask]
        label_scores = all_scores[mask]

        # Cluster overlapping boxes using simple greedy NMS-like fusion
        used = [False] * len(label_boxes)
        for i in range(len(label_boxes)):
            if used[i]:
                continue
            cluster_boxes = [label_boxes[i]]
            cluster_scores = [label_scores[i]]
            used[i] = True

            for j in range(i + 1, len(label_boxes)):
                if used[j]:
                    continue
                if _iou(label_boxes[i], label_boxes[j]) > iou_thr:
                    cluster_boxes.append(label_boxes[j])
                    cluster_scores.append(label_scores[j])
                    used[j] = True

            # Weighted average of cluster
            weights = np.array(cluster_scores)
            weights = weights / weights.sum()
            merged_box = np.average(cluster_boxes, axis=0, weights=weights)
            merged_score = np.mean(cluster_scores)

            final_boxes.append(merged_box)
            final_scores.append(merged_score)
            final_labels.append(label)

    return np.array(final_boxes), np.array(final_scores), np.array(final_labels)


def _iou(box1, box2):
    """Compute IoU between two boxes (x1, y1, x2, y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0


# ============================================================
# Class names (0-13, excluding 14="No finding")
# ============================================================
CLASS_NAMES = [
    "Aortic enlargement",    # 0
    "Atelectasis",           # 1
    "Calcification",         # 2
    "Cardiomegaly",          # 3
    "Consolidation",         # 4
    "ILD",                   # 5
    "Infiltration",          # 6
    "Lung Opacity",          # 7
    "Nodule/Mass",           # 8
    "Other lesion",          # 9
    "Pleural effusion",      # 10
    "Pleural thickening",    # 11
    "Pneumothorax",          # 12
    "Pulmonary fibrosis",    # 13
]
NUM_CLASSES = len(CLASS_NAMES)  # 14 detection classes


def get_image_display_size(row):
    """
    The CSV has scaled coordinates. The display image is 1024x1024 based on
    common VinBigData preprocessing guidelines. We use the actual image to
    determine its pixel dimensions for normalization.
    """
    # The x_min/y_min/x_max/y_max in CSV are already scaled to a display size.
    # We need to figure out what that display size is.
    # scale_x = display_width / raw_width  =>  display_width = scale_x * raw_width
    # But actually the display coords are just (x_min, y_min, x_max, y_max) directly.
    # From the data: scale_x ~ 0.34-0.51, raw_width ~ 2000-3200
    # display_width = scale_x * raw_width = ~1024
    # All images seem to be scaled to ~1024x1024
    pass


def convert_dataset(
    csv_path: str,
    images_dir: str,
    output_dir: str,
    val_split: float = 0.15,
    iou_thr: float = 0.5,
    include_no_finding_ratio: float = 1.0,
    seed: int = 42,
):
    """Main conversion pipeline."""
    random.seed(seed)
    np.random.seed(seed)

    print("=" * 60)
    print("VinBigData CSV → YOLO Format Converter")
    print("=" * 60)

    # ---- 1. Read CSV ----
    print("\n[1/6] Reading CSV...")
    df = pd.read_csv(csv_path)
    print(f"  Total rows: {len(df)}")
    print(f"  Unique images: {df['image_id'].nunique()}")

    # ---- 2. Separate finding vs no-finding images ----
    print("\n[2/6] Separating finding / no-finding images...")
    finding_df = df[df['class_id'] != 14].copy()
    no_finding_ids = df[df['class_id'] == 14]['image_id'].unique()
    finding_ids = finding_df['image_id'].unique()

    # Remove any no_finding ids that also appear in findings
    pure_no_finding = set(no_finding_ids) - set(finding_ids)

    print(f"  Images with findings: {len(finding_ids)}")
    print(f"  Pure no-finding images: {len(pure_no_finding)}")

    # Drop rows with NaN bounding boxes in the finding set
    finding_df = finding_df.dropna(subset=['x_min', 'y_min', 'x_max', 'y_max'])
    print(f"  Annotation rows with valid bboxes: {len(finding_df)}")

    # ---- 3. Get actual image sizes ----
    print("\n[3/6] Determining image sizes and aggregating annotations...")

    # We need actual image pixel sizes to normalize YOLO coords.
    # The CSV coords (x_min etc.) are in a "display" space.
    # display_size = raw_size * scale
    # So display_width = raw_width * scale_x
    # We'll compute display dimensions for each image from the CSV metadata.

    # Group by image
    image_annotations = defaultdict(list)
    image_display_sizes = {}

    for _, row in finding_df.iterrows():
        img_id = row['image_id']
        display_w = row['raw_width'] * row['scale_x']
        display_h = row['raw_height'] * row['scale_y']
        image_display_sizes[img_id] = (display_w, display_h)
        image_annotations[img_id].append(row)

    # ---- 4. Aggregate multi-radiologist annotations with WBF ----
    print("\n[4/6] Running Weighted Boxes Fusion...")

    yolo_labels = {}  # image_id -> list of "class_id x_c y_c w h"

    for img_id in image_annotations:
        rows = image_annotations[img_id]
        disp_w, disp_h = image_display_sizes[img_id]

        # Group by radiologist
        rad_groups = defaultdict(list)
        for r in rows:
            rad_groups[r['rad_id']].append(r)

        boxes_list = []
        scores_list = []
        labels_list = []

        for rad_id, rad_rows in rad_groups.items():
            boxes = []
            scores = []
            labels = []
            for r in rad_rows:
                # Normalize to 0-1 for WBF
                x1 = r['x_min'] / disp_w
                y1 = r['y_min'] / disp_h
                x2 = r['x_max'] / disp_w
                y2 = r['y_max'] / disp_h

                # Clamp
                x1 = max(0, min(1, x1))
                y1 = max(0, min(1, y1))
                x2 = max(0, min(1, x2))
                y2 = max(0, min(1, y2))

                if x2 <= x1 or y2 <= y1:
                    continue

                boxes.append([x1, y1, x2, y2])
                scores.append(1.0)  # All radiologist annotations equally weighted
                labels.append(int(r['class_id']))

            if boxes:
                boxes_list.append(np.array(boxes))
                scores_list.append(np.array(scores))
                labels_list.append(np.array(labels))

        if not boxes_list:
            continue

        # Run WBF
        merged_boxes, merged_scores, merged_labels = weighted_boxes_fusion(
            boxes_list, scores_list, labels_list, iou_thr=iou_thr
        )

        # Convert to YOLO format: class x_center y_center width height
        yolo_lines = []
        for box, label in zip(merged_boxes, merged_labels):
            x_center = (box[0] + box[2]) / 2
            y_center = (box[1] + box[3]) / 2
            width = box[2] - box[0]
            height = box[3] - box[1]

            # Clamp to valid range
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            width = max(0, min(1, width))
            height = max(0, min(1, height))

            yolo_lines.append(f"{int(label)} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        if yolo_lines:
            yolo_labels[img_id] = yolo_lines

    print(f"  Images with merged annotations: {len(yolo_labels)}")
    total_boxes = sum(len(v) for v in yolo_labels.values())
    print(f"  Total merged bounding boxes: {total_boxes}")

    # ---- 5. Split train/val ----
    print(f"\n[5/6] Splitting dataset (val_split={val_split})...")

    finding_image_list = list(yolo_labels.keys())
    random.shuffle(finding_image_list)

    val_count = int(len(finding_image_list) * val_split)
    val_images = set(finding_image_list[:val_count])
    train_images = set(finding_image_list[val_count:])

    # Include no-finding images as background (balanced with findings)
    # ratio=1.0 means same count as finding images, 0.5 means half, etc.
    no_finding_list = list(pure_no_finding)
    random.shuffle(no_finding_list)
    n_no_finding = int(len(finding_image_list) * include_no_finding_ratio)
    n_no_finding = min(n_no_finding, len(no_finding_list))
    selected_no_finding = no_finding_list[:n_no_finding]

    nf_val = int(len(selected_no_finding) * val_split)
    no_finding_val = set(selected_no_finding[:nf_val])
    no_finding_train = set(selected_no_finding[nf_val:])

    train_images.update(no_finding_train)
    val_images.update(no_finding_val)

    print(f"  Train images: {len(train_images)} ({len(train_images) - len(no_finding_train)} with findings + {len(no_finding_train)} no-finding)")
    print(f"  Val images: {len(val_images)} ({len(val_images) - len(no_finding_val)} with findings + {len(no_finding_val)} no-finding)")

    # ---- 6. Create YOLO directory structure ----
    print(f"\n[6/6] Creating YOLO dataset at {output_dir}...")

    out = Path(output_dir)
    for split in ['train', 'val']:
        (out / 'images' / split).mkdir(parents=True, exist_ok=True)
        (out / 'labels' / split).mkdir(parents=True, exist_ok=True)

    # Copy images and write labels
    images_path = Path(images_dir)
    missing = 0
    copied = 0

    for split_name, split_set in [('train', train_images), ('val', val_images)]:
        for img_id in split_set:
            src_img = images_path / f"{img_id}.jpg"
            if not src_img.exists():
                # Try .png
                src_img = images_path / f"{img_id}.png"
                if not src_img.exists():
                    missing += 1
                    continue

            # Copy image (use symlink on Windows if possible, else copy)
            dst_img = out / 'images' / split_name / f"{img_id}.jpg"
            if not dst_img.exists():
                shutil.copy2(str(src_img), str(dst_img))

            # Write label file
            dst_label = out / 'labels' / split_name / f"{img_id}.txt"
            if img_id in yolo_labels:
                with open(dst_label, 'w') as f:
                    f.write('\n'.join(yolo_labels[img_id]) + '\n')
            else:
                # No-finding: empty label file
                dst_label.touch()

            copied += 1

    if missing > 0:
        print(f"  ⚠ {missing} images not found in {images_dir}")
    print(f"  ✓ Copied {copied} images + labels")

    # Write dataset.yaml
    yaml_path = out / 'dataset.yaml'
    yaml_content = f"""# YOLOv8 Chest X-ray Dataset Config
# Auto-generated by convert_annotations.py

path: {out.resolve().as_posix()}
train: images/train
val: images/val

nc: {NUM_CLASSES}
names: {CLASS_NAMES}
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"  ✓ Created {yaml_path}")

    # Print per-class stats
    print("\n" + "=" * 60)
    print("Per-Class Statistics (after WBF):")
    print("=" * 60)
    class_counts = defaultdict(int)
    for lines in yolo_labels.values():
        for line in lines:
            cls_id = int(line.split()[0])
            class_counts[cls_id] += 1

    for i in range(NUM_CLASSES):
        count = class_counts.get(i, 0)
        print(f"  [{i:2d}] {CLASS_NAMES[i]:<25s} : {count:5d} boxes")

    print(f"\n✅ Conversion complete! Dataset ready at: {out.resolve()}")
    print(f"   Use this YAML for YOLOv8 training: {yaml_path.resolve()}")


if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent  # final/final/
    CSV_PATH = str(BASE / "dataset" / "train.csv")
    IMAGES_DIR = str(BASE / "dataset" / "train")
    OUTPUT_DIR = str(BASE / "training" / "yolo_dataset")

    convert_dataset(
        csv_path=CSV_PATH,
        images_dir=IMAGES_DIR,
        output_dir=OUTPUT_DIR,
        val_split=0.15,
        iou_thr=0.5,
        include_no_finding_ratio=1.0,
    )
