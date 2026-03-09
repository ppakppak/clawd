from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/gpu-server/api.py')
s = p.read_text()

old = """        data = request.get_json(force=True, silent=True) or {}
        annotations_data = data.get('annotations_data', [])
        selected_classes = data.get('classes', []) or []
        output_dir = data.get('output_dir', 'pipe_dataset')
        split_ratio = data.get('split_ratio', '0.7,0.15,0.15')

        if not annotations_data:
            return jsonify({'success': False, 'error': 'No annotations data provided'}), 400
"""

new = """        data = request.get_json(force=True, silent=True) or {}
        annotations_data = data.get('annotations_data', [])
        projects = data.get('projects', {}) or {}
        base_projects_dir = Path(data.get('base_projects_dir', '/home/intu/Nas2/k_water/pipe_inspector_data'))
        selected_classes = data.get('classes', []) or []
        output_dir = data.get('output_dir', 'pipe_dataset')
        split_ratio = data.get('split_ratio', '0.7,0.15,0.15')

        # Compact request mode: projects + classes만 전달받고 서버에서 어노테이션 직접 로드
        if not annotations_data and projects:
            print(f"[DATASET BUILD-FILTERED] compact mode: loading annotations from {len(projects)} projects")
            for project_id, videos in projects.items():
                project_dir = None

                # base_projects_dir/*/<project_id> 구조에서 프로젝트 탐색
                try:
                    user_dirs = sorted([d for d in base_projects_dir.iterdir() if d.is_dir()])
                except Exception:
                    user_dirs = []

                for user_dir in user_dirs:
                    cand = user_dir / project_id
                    if cand.exists() and cand.is_dir():
                        project_dir = cand
                        break

                if not project_dir:
                    continue

                annotations_dir = project_dir / 'annotations'
                if not annotations_dir.exists():
                    continue

                for video_info in videos or []:
                    video_id = video_info.get('video_id') if isinstance(video_info, dict) else None
                    if not video_id:
                        continue

                    video_annotations_dir = annotations_dir / video_id
                    if not video_annotations_dir.exists():
                        continue

                    for json_file in video_annotations_dir.glob('*.json'):
                        if json_file.stem.endswith('.backup') or 'before_fix' in json_file.name or 'discussions' in json_file.name:
                            continue
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                anno_data = json.load(f)
                            annotations_data.append({
                                'project_id': project_id,
                                'video_id': video_id,
                                'annotations': anno_data.get('annotations', {}),
                                'video_name': video_info.get('name', video_id) if isinstance(video_info, dict) else video_id,
                                'project_dir': str(project_dir),
                            })
                        except Exception as e:
                            print(f"[DATASET BUILD-FILTERED] annotation read error {json_file}: {e}")

            print(f"[DATASET BUILD-FILTERED] compact mode loaded annotation files: {len(annotations_data)}")

        if not annotations_data:
            return jsonify({'success': False, 'error': 'No annotations data provided'}), 400
"""

if old not in s:
    raise SystemExit('target block not found in gpu api')

s = s.replace(old, new, 1)

p.write_text(s)
print('patched gpu-server/api.py for compact mode')
