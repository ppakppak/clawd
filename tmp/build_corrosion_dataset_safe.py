#!/usr/bin/env python3
import json
import random
from pathlib import Path
from datetime import datetime
from collections import Counter
import cv2

BASE_DIR = Path('/home/intu/Nas2/k_water/pipe_inspector_data')
VIDEOS_WEB_DIR = Path('/home/intu/nas2_kwater/Videos_web')
OUTPUT_ROOT = Path('/home/intu/projects/pipe-inspector-staging/gpu-server')
OUTPUT_PREFIX = 'pipe_dataset_corrosion2'
TARGET_CLASSES = ['부식(결절)', '부식(녹)']
CLASS_TO_ID = {cls: idx for idx, cls in enumerate(TARGET_CLASSES)}
SPLIT_RATIO = (0.7, 0.15, 0.15)


def find_web_video_path(original_path: str) -> Path:
    p = Path(original_path)
    s = str(p)
    if 'SAHARA' in s:
        parts = list(p.parts)
        i = parts.index('SAHARA')
        rel = Path(*parts[i+1:])
        return (VIDEOS_WEB_DIR / 'SAHARA' / rel).with_suffix('.mp4')
    if '관내시경영상' in s:
        parts = list(p.parts)
        i = parts.index('관내시경영상')
        rel = Path(*parts[i+1:])
        return (VIDEOS_WEB_DIR / '관내시경영상' / rel).with_suffix('.mp4')
    return p


def polygon_to_yolo(points, w, h):
    out = []
    for pt in points:
        x = max(0.0, min(1.0, float(pt['x']) / w))
        y = max(0.0, min(1.0, float(pt['y']) / h))
        out.append(f"{x:.6f} {y:.6f}")
    return ' '.join(out)


def collect_frames():
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
                project = json.loads(project_json.read_text())
            except Exception:
                continue

            video_map = {}
            for v in project.get('videos', []):
                vid = v.get('video_id')
                vpath = v.get('video_path')
                if not vid or not vpath:
                    continue
                web_path = find_web_video_path(vpath)
                video_map[vid] = {
                    'path': web_path,
                    'width': v.get('width', 1920),
                    'height': v.get('height', 1080),
                }

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
                    n = jf.name
                    if 'discussions' in n or 'backup' in n or 'before_fix' in n:
                        continue
                    try:
                        data = json.loads(jf.read_text())
                    except Exception:
                        continue

                    annos = data.get('annotations', {})
                    if not isinstance(annos, dict):
                        continue

                    for frame_num, frame_labels in annos.items():
                        if not isinstance(frame_labels, list):
                            continue
                        filtered = []
                        for lbl in frame_labels:
                            name = lbl.get('label', '')
                            poly = lbl.get('polygon') or []
                            if name in CLASS_TO_ID and len(poly) >= 3:
                                filtered.append({
                                    'class_id': CLASS_TO_ID[name],
                                    'class_name': name,
                                    'polygon': poly,
                                })
                                label_counts[name] += 1
                        if filtered:
                            frames.append({
                                'key': f"{vid}_{int(frame_num):06d}",
                                'video_path': str(vinfo['path']),
                                'frame_num': int(frame_num),
                                'labels': filtered,
                            })

    uniq = {}
    for f in frames:
        uniq.setdefault(f['key'], f)
    unique_frames = list(uniq.values())

    print('Collected unique frames:', len(unique_frames))
    print('Label counts:', dict(label_counts))
    return unique_frames


def build_dataset(frames):
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

    out = OUTPUT_ROOT / f"{OUTPUT_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for split in ['train', 'val', 'test']:
        (out / split / 'images').mkdir(parents=True, exist_ok=True)
        (out / split / 'labels').mkdir(parents=True, exist_ok=True)

    counts = {k: 0 for k in splits}

    for split, items in splits.items():
        print(f"Processing {split}: {len(items)}")
        for i, item in enumerate(items, 1):
            cap = cv2.VideoCapture(item['video_path'])
            cap.set(cv2.CAP_PROP_POS_FRAMES, item['frame_num'])
            ok, img = cap.read()
            cap.release()
            if not ok or img is None:
                continue

            h, w = img.shape[:2]
            fname = item['key'].replace('/', '_')
            img_path = out / split / 'images' / f"{fname}.jpg"
            lab_path = out / split / 'labels' / f"{fname}.txt"
            cv2.imwrite(str(img_path), img)

            lines = []
            for lbl in item['labels']:
                poly = polygon_to_yolo(lbl['polygon'], w, h)
                lines.append(f"{lbl['class_id']} {poly}")
            lab_path.write_text('\n'.join(lines))
            counts[split] += 1

            if i % 100 == 0:
                print(f"  {split}: {i}/{len(items)}")

    data_yaml = (
        f"path: {out}\n"
        "train: train/images\n"
        "val: val/images\n"
        "test: test/images\n"
        f"nc: {len(TARGET_CLASSES)}\n"
        f"names: {TARGET_CLASSES}\n"
    )
    (out / 'data.yaml').write_text(data_yaml)

    info = {
        'created_at': datetime.now().isoformat(),
        'total_frames': sum(counts.values()),
        'train_count': counts['train'],
        'val_count': counts['val'],
        'test_count': counts['test'],
        'split_ratio': ','.join(map(str, SPLIT_RATIO)),
        'num_classes': len(TARGET_CLASSES),
        'class_names': TARGET_CLASSES,
    }
    (out / 'dataset_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))

    print('Done dataset:', out)
    print('Counts:', counts)
    return out


def main():
    print('=' * 60)
    print('Build corrosion 2-class dataset (safe)')
    print('Classes:', TARGET_CLASSES)
    print('=' * 60)

    frames = collect_frames()
    if not frames:
        raise SystemExit('No frames found')

    out = build_dataset(frames)
    print('OUTPUT=', out)


if __name__ == '__main__':
    main()
