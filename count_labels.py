#!/usr/bin/env python3
"""Count label distribution across all annotations"""
import json, os, glob
from collections import Counter

base = '/home/intu/Nas2/k_water/pipe_inspector_data'
label_counts = Counter()
label_frames = Counter()  # frames containing each label

for anno_file in glob.glob(os.path.join(base, '*/*/annotations/*/*.json')):
    if 'discussions.json' in anno_file:
        continue
    try:
        with open(anno_file) as f:
            data = json.load(f)
        annos = data.get('annotations', {})
        for frame_id, frame_labels in annos.items():
            if isinstance(frame_labels, list):
                seen = set()
                for lbl in frame_labels:
                    name = lbl.get('label', 'unknown')
                    label_counts[name] += 1
                    seen.add(name)
                for name in seen:
                    label_frames[name] += 1
    except Exception:
        pass

print("=== Label Distribution ===")
print(f"{'Label':<30} {'Count':>8} {'Frames':>8}")
print("-" * 50)
for label, count in label_counts.most_common():
    frames = label_frames[label]
    print(f"{label:<30} {count:>8} {frames:>8}")
print("-" * 50)
print(f"{'TOTAL':<30} {sum(label_counts.values()):>8}")
