from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/gpu-server/api.py')
s = p.read_text()

anchor = """
# ============================================================
# YOLO Training API
# ============================================================
"""

if anchor not in s:
    raise SystemExit('anchor not found')

if '/api/dataset/build_yolo_filtered' in s:
    print('already patched')
    raise SystemExit(0)

insert = r'''

@app.route('/api/dataset/build_yolo_filtered', methods=['POST'])
def build_yolo_dataset_filtered():
    """다중 프로젝트 YOLO 데이터셋 빌드 (클래스 필터 + class id 재매핑)"""
    from pathlib import Path
    import random
    from datetime import datetime
    from collections import defaultdict
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        data = request.get_json(force=True, silent=True) or {}
        annotations_data = data.get('annotations_data', [])
        selected_classes = data.get('classes', []) or []
        output_dir = data.get('output_dir', 'pipe_dataset')
        split_ratio = data.get('split_ratio', '0.7,0.15,0.15')

        if not annotations_data:
            return jsonify({'success': False, 'error': 'No annotations data provided'}), 400

        selected_classes = [c for c in selected_classes if isinstance(c, str) and c.strip()]
        selected_set = set(selected_classes)

        output_path = Path(output_dir)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_dir
        if output_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_path.parent / f"{output_path.name}_{timestamp}"

        for split in ['train', 'val', 'test']:
            (output_path / split / 'images').mkdir(parents=True, exist_ok=True)
            (output_path / split / 'labels').mkdir(parents=True, exist_ok=True)

        try:
            tr, vr, ter = map(float, str(split_ratio).split(','))
            total = tr + vr + ter
            if total <= 0:
                raise ValueError('Invalid split ratio')
            train_ratio, val_ratio, test_ratio = tr / total, vr / total, ter / total
        except Exception:
            train_ratio, val_ratio, test_ratio = 0.7, 0.15, 0.15

        korean_to_english = {
            '정상부': 'normal',
            '변형': 'deformation',
            '균열': 'crack',
            '부식': 'corrosion',
            '부식(결절)': 'corrosion_nodule',
            '부식(녹)': 'corrosion_rust',
            '침전물(흙)': 'sediment_soil',
            '침전물(모래)': 'sediment_sand',
            '침전물(부식 생성물)': 'sediment_corrosion',
            '침전물(탈리, 도장재)': 'sediment_coating',
            '침전물(기타)': 'sediment_other',
            '슬라임(물때)': 'slime',
            '논의필요': 'needs_discussion',
            '소실점': 'vanishing_point',
        }

        project_cache = {}

        def resolve_video_path(project_dir: Path, video_id: str):
            pkey = str(project_dir)
            if pkey not in project_cache:
                project_file = project_dir / 'project.json'
                video_map = {}
                class_map = {}
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            pj = json.load(f)
                        for idx, cls in enumerate(pj.get('classes', [])):
                            class_map[idx] = cls.get('name', f'class_{idx}')
                        for v in pj.get('videos', []):
                            vid = v.get('video_id')
                            if vid:
                                video_map[vid] = v.get('video_path')
                    except Exception as e:
                        print(f"[DATASET BUILD-FILTERED] project.json parse error: {project_file}: {e}")
                project_cache[pkey] = {'video_map': video_map, 'class_map': class_map}

            meta = project_cache[pkey]
            src_path = meta['video_map'].get(video_id)
            if not src_path:
                return None, meta['class_map']

            src = str(src_path)
            src_path_obj = Path(src_path)
            if 'SAHARA' in src:
                parts = list(src_path_obj.parts)
                i = parts.index('SAHARA')
                rel = Path(*parts[i+1:])
                web_path = Path('/home/intu/nas2_kwater/Videos_web/SAHARA') / rel
                web_path = web_path.with_suffix('.mp4')
            elif '관내시경영상' in src:
                parts = list(src_path_obj.parts)
                i = parts.index('관내시경영상')
                rel = Path(*parts[i+1:])
                web_path = Path('/home/intu/nas2_kwater/Videos_web/관내시경영상') / rel
                web_path = web_path.with_suffix('.mp4')
            else:
                web_path = Path(src.replace('.avi', '.mp4').replace('.AVI', '.mp4'))

            return str(web_path), meta['class_map']

        all_frames = []
        unique_keys = set()
        class_order = list(dict.fromkeys(selected_classes)) if selected_classes else []

        for anno_data in annotations_data:
            project_id = anno_data.get('project_id', '')
            video_id = anno_data.get('video_id', '')
            annotations = anno_data.get('annotations', {}) or {}
            project_dir = Path(anno_data.get('project_dir', ''))

            video_path, class_map = resolve_video_path(project_dir, video_id)
            if not video_path:
                continue
            if not Path(video_path).exists():
                continue

            for frame_num_str, frame_annos in annotations.items():
                if not isinstance(frame_annos, list) or not frame_annos:
                    continue

                try:
                    frame_num = int(frame_num_str)
                except Exception:
                    continue

                filtered_annos = []
                for anno in frame_annos:
                    polygon = anno.get('polygon')
                    if not isinstance(polygon, list) or len(polygon) < 3:
                        continue

                    label = anno.get('label')
                    if not label:
                        class_id = anno.get('class_id')
                        if isinstance(class_id, int):
                            label = class_map.get(class_id)
                        else:
                            try:
                                label = class_map.get(int(class_id))
                            except Exception:
                                label = None

                    if not label:
                        continue
                    if selected_set and label not in selected_set:
                        continue

                    if not selected_set and label not in class_order:
                        class_order.append(label)

                    filtered_annos.append({'label': label, 'polygon': polygon})

                if not filtered_annos:
                    continue

                unique_key = f"{project_id}::{video_id}::{frame_num}"
                if unique_key in unique_keys:
                    continue
                unique_keys.add(unique_key)

                all_frames.append({
                    'project_id': project_id,
                    'video_id': video_id,
                    'video_path': video_path,
                    'frame_num': frame_num,
                    'annotations': filtered_annos,
                })

        if not all_frames:
            return jsonify({'success': False, 'error': 'No frames with selected annotations found'}), 400
        if not class_order:
            return jsonify({'success': False, 'error': 'No classes resolved from annotations'}), 400

        class_to_id = {name: idx for idx, name in enumerate(class_order)}
        yaml_names = [korean_to_english.get(name, name) for name in class_order]

        print(f"[DATASET BUILD-FILTERED] Frames: {len(all_frames)}")
        print(f"[DATASET BUILD-FILTERED] Classes: {class_order}")

        random.shuffle(all_frames)
        train_end = int(len(all_frames) * train_ratio)
        val_end = train_end + int(len(all_frames) * val_ratio)
        train_frames = all_frames[:train_end]
        val_frames = all_frames[train_end:val_end]
        test_frames = all_frames[val_end:]

        def process_frames(frames, split_name):
            saved_count = 0
            frames_by_video = defaultdict(list)
            for frame_data in frames:
                frames_by_video[frame_data['video_path']].append(frame_data)

            def process_video(video_path, video_frames):
                local_count = 0
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    print(f"[DATASET BUILD-FILTERED] Cannot open video: {video_path}")
                    return 0
                try:
                    video_frames.sort(key=lambda x: x['frame_num'])
                    for frame_data in video_frames:
                        fnum = frame_data['frame_num']
                        cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            continue

                        image_filename = f"{frame_data['project_id']}_{frame_data['video_id']}_frame{fnum}.jpg"
                        image_path = output_path / split_name / 'images' / image_filename
                        label_path = output_path / split_name / 'labels' / image_filename.replace('.jpg', '.txt')

                        cv2.imwrite(str(image_path), frame)

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
                    cap.release()

                return local_count

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(process_video, vp, vf) for vp, vf in frames_by_video.items()]
                for fut in as_completed(futures):
                    try:
                        saved_count += fut.result()
                    except Exception as e:
                        print(f"[DATASET BUILD-FILTERED] Video worker error: {e}")

            return saved_count

        train_count = process_frames(train_frames, 'train')
        val_count = process_frames(val_frames, 'val')
        test_count = process_frames(test_frames, 'test')

        yaml_content = (
            f"# YOLO Dataset Configuration\\n"
            f"path: {output_path}\\n"
            "train: train/images\\n"
            "val: val/images\\n"
            "test: test/images\\n\\n"
            f"# Number of classes\\n"
            f"nc: {len(yaml_names)}\\n\\n"
            f"# Class names\\n"
            f"names: {yaml_names}\\n"
        )
        with open(output_path / 'data.yaml', 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        info = {
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
        with open(output_path / 'dataset_info.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        print(f"[DATASET BUILD-FILTERED] ✅ Complete: {output_path}")

        return jsonify({
            'success': True,
            'output_dir': str(output_path),
            'total_images': train_count + val_count + test_count,
            'train_count': train_count,
            'val_count': val_count,
            'test_count': test_count,
            'classes': class_order,
            'class_names_yaml': yaml_names,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

'''

s = s.replace(anchor, insert + anchor, 1)
p.write_text(s)
print('patched gpu-server/api.py')
