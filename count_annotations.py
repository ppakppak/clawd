#!/usr/bin/env python3
import json, os, glob

base = '/home/intu/Nas2/k_water/pipe_inspector_data'
project_stats = {}

for anno_file in glob.glob(os.path.join(base, '*/*/annotations/*/*.json')):
    if 'discussions.json' in anno_file:
        continue
    try:
        with open(anno_file) as f:
            data = json.load(f)
        annos = data.get('annotations', {})
        proj = data.get('project_id', 'unknown')
        frames = 0
        labels = 0
        for frame_id, frame_labels in annos.items():
            if isinstance(frame_labels, list) and len(frame_labels) > 0:
                frames += 1
                labels += len(frame_labels)
        if proj not in project_stats:
            project_stats[proj] = [0, 0]
        project_stats[proj][0] += frames
        project_stats[proj][1] += labels
    except Exception:
        pass

total_frames = sum(v[0] for v in project_stats.values())
total_labels = sum(v[1] for v in project_stats.values())
print(f"Total: {total_frames} frames, {total_labels} labels")
print()
for proj in sorted(project_stats, key=lambda x: project_stats[x][0], reverse=True):
    f, l = project_stats[proj]
    print(f"  {proj}: {f} frames, {l} labels")
