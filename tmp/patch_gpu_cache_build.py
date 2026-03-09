from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/gpu-server/api.py')
s = p.read_text()

old_import = """    from pathlib import Path
    import random
    from datetime import datetime
    from collections import defaultdict
    from concurrent.futures import ThreadPoolExecutor, as_completed
"""
new_import = """    from pathlib import Path
    import random
    import hashlib
    import shutil
    from datetime import datetime
    from collections import defaultdict
    from concurrent.futures import ThreadPoolExecutor, as_completed
"""
if old_import in s:
    s = s.replace(old_import, new_import, 1)
else:
    raise SystemExit('import block not found')

start_marker = "        def process_frames(frames, split_name):\n"
end_marker = "        train_count = process_frames(train_frames, 'train')\n"
start = s.find(start_marker)
if start == -1:
    raise SystemExit('process_frames start not found')
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit('process_frames end marker not found')

new_block = """        frame_cache_root = Path(__file__).parent / 'frame_cache'

        def get_cache_path(video_path, frame_num):
            key = hashlib.sha1(video_path.encode('utf-8')).hexdigest()
            return frame_cache_root / key[:2] / key / f"{int(frame_num):06d}.jpg"

        def process_frames(frames, split_name):
            saved_count = 0
            cache_hits = 0
            cache_misses = 0

            frames_by_video = defaultdict(list)
            for frame_data in frames:
                frames_by_video[frame_data['video_path']].append(frame_data)

            def process_video(video_path, video_frames):
                local_count = 0
                local_hits = 0
                local_misses = 0
                cap = None

                try:
                    video_frames.sort(key=lambda x: x['frame_num'])

                    for frame_data in video_frames:
                        fnum = frame_data['frame_num']
                        image_filename = f"{frame_data['project_id']}_{frame_data['video_id']}_frame{fnum}.jpg"
                        image_path = output_path / split_name / 'images' / image_filename
                        label_path = output_path / split_name / 'labels' / image_filename.replace('.jpg', '.txt')

                        cache_path = get_cache_path(video_path, fnum)
                        frame = None

                        # 1) 캐시 우선 사용
                        if cache_path.exists():
                            frame = cv2.imread(str(cache_path))
                            if frame is not None:
                                local_hits += 1
                                try:
                                    os.link(str(cache_path), str(image_path))
                                except Exception:
                                    shutil.copy2(str(cache_path), str(image_path))

                        # 2) 캐시 미스면 비디오에서 추출 + 캐시에 저장
                        if frame is None:
                            local_misses += 1

                            if cap is None:
                                cap = cv2.VideoCapture(video_path)
                                if not cap.isOpened():
                                    print(f"[DATASET BUILD-FILTERED] Cannot open video: {video_path}")
                                    break

                            cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
                            ret, frame = cap.read()
                            if not ret or frame is None:
                                continue

                            cv2.imwrite(str(image_path), frame)

                            try:
                                cache_path.parent.mkdir(parents=True, exist_ok=True)
                                if not cache_path.exists():
                                    cv2.imwrite(str(cache_path), frame)
                            except Exception as e:
                                print(f"[DATASET BUILD-FILTERED] cache write failed: {cache_path} ({e})")

                        h, w = frame.shape[:2]
                        lines = []
                        for anno in frame_data['annotations']:
                            cid = class_to_id.get(anno['label'])
                            if cid is None:
                                continue
                            coords = []
                            for point in anno['polygon']:
                                try:
                                    x = float(point['x']) / w
                                    y = float(point['y']) / h
                                except Exception:
                                    x = float(point[0]) / w
                                    y = float(point[1]) / h
                                x = max(0.0, min(1.0, x))
                                y = max(0.0, min(1.0, y))
                                coords.append(f"{x:.6f} {y:.6f}")
                            if len(coords) >= 3:
                                lines.append(f"{cid} " + ' '.join(coords))

                        if lines:
                            with open(label_path, 'w', encoding='utf-8') as f:
                                f.write('\\n'.join(lines))
                            local_count += 1
                        else:
                            try:
                                image_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                finally:
                    if cap is not None:
                        cap.release()

                return local_count, local_hits, local_misses

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(process_video, vp, vf) for vp, vf in frames_by_video.items()]
                for fut in as_completed(futures):
                    try:
                        c, h, m = fut.result()
                        saved_count += c
                        cache_hits += h
                        cache_misses += m
                    except Exception as e:
                        print(f"[DATASET BUILD-FILTERED] Video worker error: {e}")

            print(f"[DATASET BUILD-FILTERED] {split_name}: saved={saved_count}, cache_hit={cache_hits}, cache_miss={cache_misses}")
            return saved_count, cache_hits, cache_misses

        train_count, train_hits, train_misses = process_frames(train_frames, 'train')
        val_count, val_hits, val_misses = process_frames(val_frames, 'val')
        test_count, test_hits, test_misses = process_frames(test_frames, 'test')
"""

s = s[:start] + new_block + s[end + len(end_marker):]

# info dict에 캐시 통계 추가
old_info = """        info = {
            'created_at': datetime.now().isoformat(),
            'total_frames': len(all_frames),
            'train_count': train_count,
            'val_count': val_count,
            'test_count': test_count,
            'split_ratio': split_ratio,
            'format': 'yolo_segmentation',
            'num_classes': len(class_order),
            'class_names': class_order,
            'class_names_yaml': yaml_names,
            'selected_classes': selected_classes,
        }
"""
new_info = """        info = {
            'created_at': datetime.now().isoformat(),
            'total_frames': len(all_frames),
            'train_count': train_count,
            'val_count': val_count,
            'test_count': test_count,
            'split_ratio': split_ratio,
            'format': 'yolo_segmentation',
            'num_classes': len(class_order),
            'class_names': class_order,
            'class_names_yaml': yaml_names,
            'selected_classes': selected_classes,
            'cache': {
                'cache_dir': str(frame_cache_root),
                'hits': train_hits + val_hits + test_hits,
                'misses': train_misses + val_misses + test_misses,
                'by_split': {
                    'train': {'hit': train_hits, 'miss': train_misses},
                    'val': {'hit': val_hits, 'miss': val_misses},
                    'test': {'hit': test_hits, 'miss': test_misses},
                }
            }
        }
"""
if old_info in s:
    s = s.replace(old_info, new_info, 1)
else:
    raise SystemExit('info block not found')

p.write_text(s)
print('patched build_yolo_filtered cache-first mode')
