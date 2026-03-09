#!/usr/bin/env python3
"""
2-class corrosion dataset builder
Classes: 부식(결절), 부식(녹)
Scans ALL projects under pipe_inspector_data
"""
import json
import os
import random
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path('/home/intu/Nas2/k_water/pipe_inspector_data')
VIDEOS_WEB_DIR = Path('/home/intu/nas2_kwater/Videos_web')
OUTPUT_DIR = Path('/home/intu/projects/pipe-inspector-staging/gpu-server/pipe_dataset_corrosion')

TARGET_CLASSES = ['부식(결절)', '부식(녹)']
CLASS_TO_ID = {cls: idx for idx, cls in enumerate(TARGET_CLASSES)}
SPLIT_RATIO = (0.7, 0.15, 0.15)


def find_web_video_path(original_path):
    """Find web-compatible video path"""
    original_path = Path(original_path)
    if 'SAHARA' in str(original_path):
        parts = list(original_path.parts)
        idx = parts.index('SAHARA')
        rel = Path(*parts[idx+1:])
        return (VIDEOS_WEB_DIR / 'SAHARA' / rel).with_suffix('.mp4')
    elif '관내시경영상' in str(original_path):
        parts = list(original_path.parts)
        idx = parts.index('관내시경영상')
        rel = Path(*parts[idx+1:])
        return (VIDEOS_WEB_DIR / '관내시경영상' / rel).with_suffix('.mp4')
    return original_path


def polygon_to_yolo(points, img_w, img_h):
    """Convert polygon points to YOLO normalized format"""
    parts = []
    for pt in points:
        x = max(0.0, min(1.0, pt['x'] / img_w))
        y = max(0.0, min(1.0, pt['y'] / img_h))
        parts.append(f"{x:.6f} {y:.6f}")
    return ' '.join(parts)


def collect_all_frames():
    """Collect all frames with corrosion annotations across all projects"""
    frames = []
    label_counts = Counter()

    for user_dir in sorted(BASE_DIR.iterdir()):
        if not user_dir.is_dir():
            continue
        for project_dir in sorted(user_dir.iterdir()):
            if not project_dir.is_dir():
                continue

            project_json = project_dir / 'project.json'
            if not project_json.exists():
                continue

            try:
                with open(project_json) as f:
                    project = json.load(f)
            except Exception:
                continue

            # Build video path map
            video_map = {}
            for v in project.get('videos', []):
                vid = v['video_id']
                web_path = find_web_video_path(v['video_path'])
                video_map[vid] = {
                    'path': web_path,
                    'width': v.get('width', 1920),
                    'height': v.get('height', 1080),
                }

            # Scan annotations
            anno_dir = project_dir / 'annotations'
            if not anno_dir.exists():
                continue

            for video_folder in sorted(anno_dir.iterdir()):
                if not video_folder.is_dir():
                    continue
                vid = video_folder.name
                if vid not in video_map:
                    continue
                vinfo = video_map[vid]
                if not vinfo['path'].exists():
                    continue

                for jf in video_folder.glob('*.json'):
                    if 'discussions' in jf.name or 'backup' in jf.name:
                        continue
                    try:
                        with open(jf) as f:
                            data = json.load(f)
                    except Exception:
                        continue

                    annos = data.get('annotations', {})
                    for frame_num, frame_labels in annos.items():
                        if not isinstance(frame_labels, list):
                            continue
                        filtered = []
                        for lbl in frame_labels:
                            label_name = lbl.get('label', '')
                            if label_name in CLASS_TO_ID and lbl.get('polygon'):
                                filtered.append({
                                    'class_id': CLASS_TO_ID[label_name],
                                    'class_name': label_name,
                                    'polygon': lbl['polygon'],
                                })
                                label_counts[label_name] += 1
                        if filtered:
                            # Use unique key to avoid duplicates
                            key = f"{vid}_{frame_num}"
                            frames.append({
                                'key': key,
                                'video_path': str(vinfo['path']),
                                'frame_num': int(frame_num),
                                'width': vinfo['width'],
                                'height': vinfo['height'],
                                'labels': filtered,
                            })

    # Deduplicate by key (same frame from different users → take first)
    seen = set()
    unique_frames = []
    for f in frames:
        if f['key'] not in seen:
            seen.add(f['key'])
            unique_frames.append(f)

    print(f"Collected {len(unique_frames)} unique frames")
    print(f"Label distribution: {dict(label_counts)}")
    return unique_frames


def extract_frame(video_path, frame_num):
    """Extract a single frame from video"""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def build_dataset(frames):
    """Build YOLO segmentation dataset"""
    random.seed(42)
    random.shuffle(frames)

    n = len(frames)
    n_train = int(n * SPLIT_RATIO[0])
    n_val = int(n * SPLIT_RATIO[1])

    splits = {
        'train': frames[:n_train],
        'val': frames[n_train:n_train+n_val],
        'test': frames[n_train+n_val:],
    }

    # Create output dirs
    out = OUTPUT_DIR
    if out.exists():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = out.parent / f"{out.name}_{ts}"

    for split in ['train', 'val', 'test']:
        (out / split / 'images').mkdir(parents=True, exist_ok=True)
        (out / split / 'labels').mkdir(parents=True, exist_ok=True)

    counts = {'train': 0, 'val': 0, 'test': 0}
    video_cache = {}

    for split, split_frames in splits.items():
        print(f"\nProcessing {split}: {len(split_frames)} frames")
        for i, frame_info in enumerate(split_frames):
            vpath = frame_info['video_path']
            fnum = frame_info['frame_num']
            w = frame_info['width']
            h = frame_info['height']

            # Extract frame (cache video capture)
            if vpath not in video_cache:
                video_cache[vpath] = cv2.VideoCapture(vpath)
            cap = video_cache[vpath]
            cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
            ret, img = cap.read()
            if not ret:
                continue

            # Actual image dimensions
            actual_h, actual_w = img.shape[:2]

            # Save image
            fname = f"{frame_info['key'].replace('/', '_')}"
            img_path = out / split / 'images' / f"{fname}.jpg"
            cv2.imwrite(str(img_path), img)

            # Save YOLO label
            label_lines = []
            for lbl in frame_info['labels']:
                poly = lbl['polygon']
                if len(poly) < 3:
                    continue
                yolo_poly = polygon_to_yolo(poly, actual_w, actual_h)
                label_lines.append(f"{lbl['class_id']} {yolo_poly}")

            label_path = out / split / 'labels' / f"{fname}.txt"
            with open(label_path, 'w') as f:
                f.write('\n'.join(label_lines))

            counts[split] += 1

            if (i + 1) % 100 == 0:
                print(f"  {split}: {i+1}/{len(split_frames)}")

    # Close video captures
    for cap in video_cache.values():
        cap.release()

    # Write data.yaml
    yaml_content = f"""# YOLO Dataset Configuration
path: {out}
train: train/images
val: val/images
test: test/images

# Number of classes
nc: {len(TARGET_CLASSES)}

# Class names
names: {TARGET_CLASSES}
"""
    with open(out / 'data.yaml', 'w') as f:
        f.write(yaml_content)

    # Write dataset_info.json
    info = {
        'created_at': datetime.now().isoformat(),
        'total_frames': sum(counts.values()),
        'train_count': counts['train'],
        'val_count': counts['val'],
        'test_count': counts['test'],
        'split_ratio': f"{SPLIT_RATIO[0]},{SPLIT_RATIO[1]},{SPLIT_RATIO[2]}",
        'format': 'yolo_segmentation',
        'num_classes': len(TARGET_CLASSES),
        'class_names': TARGET_CLASSES,
    }
    with open(out / 'dataset_info.json', 'w') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Dataset built: {out}")
    print(f"   Train: {counts['train']}, Val: {counts['val']}, Test: {counts['test']}")
    print(f"   Total: {sum(counts.values())}")
    return str(out)


if __name__ == '__main__':
    print("=" * 60)
    print("Building 2-class corrosion dataset")
    print(f"Classes: {TARGET_CLASSES}")
    print("=" * 60)

    frames = collect_all_frames()
    if not frames:
        print("No frames found!")
        exit(1)

    output = build_dataset(frames)
    print(f"\nDone! Dataset at: {output}")
