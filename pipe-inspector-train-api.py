"""
YOLO Training API endpoints for pipe-inspector gpu-server
Append this before `if __name__ == '__main__':` in api.py
"""

# ============================================================
# YOLO Training API
# ============================================================

# 학습 상태 관리
training_state = {
    'is_training': False,
    'job_id': None,
    'progress': {},
    'cancel_requested': False,
    'thread': None
}
training_lock = threading.Lock()


def _run_yolo_training(job_id, config):
    """백그라운드 YOLO 학습 실행"""
    global training_state

    try:
        from ultralytics import YOLO
        import time

        dataset_path = config['dataset_path']
        data_yaml = os.path.join(dataset_path, 'data.yaml')

        if not os.path.exists(data_yaml):
            with training_lock:
                training_state['progress'] = {
                    'status': 'error',
                    'error': f'data.yaml not found: {data_yaml}'
                }
                training_state['is_training'] = False
            return

        # 모델 선택
        model_size = config.get('model_size', 'n')  # n, s, m, l, x
        base_model = config.get('base_model', f'yolov8{model_size}-seg.pt')

        # 기존 모델에서 이어서 학습 (resume/transfer)
        resume_from = config.get('resume_from')
        if resume_from and os.path.exists(resume_from):
            print(f"[TRAIN] Resuming from: {resume_from}")
            model = YOLO(resume_from)
        else:
            print(f"[TRAIN] Starting from: {base_model}")
            model = YOLO(base_model)

        # 학습 파라미터
        epochs = config.get('epochs', 100)
        batch_size = config.get('batch_size', 8)
        img_size = config.get('img_size', 640)
        patience = config.get('patience', 20)
        lr0 = config.get('lr0', 0.01)
        project_name = config.get('project_name', 'pipe_defect')

        # 저장 경로
        script_dir = os.path.dirname(os.path.abspath(__file__))
        runs_dir = os.path.join(script_dir, 'runs')

        with training_lock:
            training_state['progress'] = {
                'status': 'starting',
                'job_id': job_id,
                'config': {
                    'base_model': base_model,
                    'dataset': dataset_path,
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'img_size': img_size,
                },
                'epoch': 0,
                'total_epochs': epochs,
                'metrics': {}
            }

        print(f"[TRAIN] Starting training job {job_id}")
        print(f"[TRAIN] Dataset: {dataset_path}")
        print(f"[TRAIN] Model: {base_model}, Epochs: {epochs}, Batch: {batch_size}")

        # 콜백으로 진행률 추적
        def on_train_epoch_end(trainer):
            if training_state['cancel_requested']:
                raise KeyboardInterrupt("Training cancelled by user")

            epoch = trainer.epoch + 1
            metrics = {}
            if hasattr(trainer, 'metrics'):
                for k, v in trainer.metrics.items():
                    try:
                        metrics[k] = float(v)
                    except (TypeError, ValueError):
                        pass

            loss_items = {}
            if hasattr(trainer, 'loss_items') and trainer.loss_items is not None:
                loss_names = ['box_loss', 'seg_loss', 'cls_loss', 'dfl_loss']
                for i, name in enumerate(loss_names):
                    if i < len(trainer.loss_items):
                        try:
                            loss_items[name] = float(trainer.loss_items[i])
                        except (TypeError, ValueError):
                            pass

            with training_lock:
                training_state['progress'].update({
                    'status': 'training',
                    'epoch': epoch,
                    'total_epochs': epochs,
                    'metrics': metrics,
                    'loss': loss_items,
                    'percent': round(epoch / epochs * 100, 1)
                })

            print(f"[TRAIN] Epoch {epoch}/{epochs} - Loss: {loss_items} - Metrics: {metrics}")

        def on_train_start(trainer):
            with training_lock:
                training_state['progress']['status'] = 'training'

        # 콜백 등록
        model.add_callback('on_train_epoch_end', on_train_epoch_end)
        model.add_callback('on_train_start', on_train_start)

        # 학습 실행
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            patience=patience,
            lr0=lr0,
            project=runs_dir,
            name=project_name,
            exist_ok=False,
            device=0,
            workers=4,
            verbose=True,
            save=True,
            save_period=10,  # 10 에폭마다 체크포인트
            plots=True,
        )

        # 학습 완료 — best.pt 경로 찾기
        best_model_path = None
        if hasattr(results, 'save_dir'):
            best_path = os.path.join(str(results.save_dir), 'weights', 'best.pt')
            if os.path.exists(best_path):
                best_model_path = best_path

        # 최종 메트릭
        final_metrics = {}
        if results and hasattr(results, 'results_dict'):
            for k, v in results.results_dict.items():
                try:
                    final_metrics[k] = float(v)
                except (TypeError, ValueError):
                    pass

        with training_lock:
            training_state['progress'].update({
                'status': 'completed',
                'epoch': epochs,
                'percent': 100.0,
                'best_model': best_model_path,
                'final_metrics': final_metrics,
                'save_dir': str(results.save_dir) if hasattr(results, 'save_dir') else None
            })
            training_state['is_training'] = False

        print(f"[TRAIN] ✅ Training complete! Best model: {best_model_path}")

    except KeyboardInterrupt:
        with training_lock:
            training_state['progress']['status'] = 'cancelled'
            training_state['is_training'] = False
        print(f"[TRAIN] ⚠️ Training cancelled")

    except Exception as e:
        import traceback
        traceback.print_exc()
        with training_lock:
            training_state['progress'] = {
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            training_state['is_training'] = False
        print(f"[TRAIN] ❌ Training error: {e}")


@app.route('/api/ai/train', methods=['POST'])
def start_training():
    """YOLO 학습 시작"""
    global training_state

    with training_lock:
        if training_state['is_training']:
            return jsonify({
                'success': False,
                'error': 'Training already in progress',
                'job_id': training_state['job_id']
            }), 409

    data = request.json or {}
    dataset_path = data.get('dataset_path')

    if not dataset_path:
        return jsonify({
            'success': False,
            'error': 'dataset_path is required'
        }), 400

    if not os.path.exists(dataset_path):
        return jsonify({
            'success': False,
            'error': f'Dataset not found: {dataset_path}'
        }), 404

    import uuid
    job_id = str(uuid.uuid4())[:8]

    config = {
        'dataset_path': dataset_path,
        'model_size': data.get('model_size', 'n'),
        'base_model': data.get('base_model'),
        'resume_from': data.get('resume_from'),
        'epochs': data.get('epochs', 100),
        'batch_size': data.get('batch_size', 8),
        'img_size': data.get('img_size', 640),
        'patience': data.get('patience', 20),
        'lr0': data.get('lr0', 0.01),
        'project_name': data.get('project_name', 'pipe_defect'),
    }

    with training_lock:
        training_state['is_training'] = True
        training_state['job_id'] = job_id
        training_state['cancel_requested'] = False
        training_state['progress'] = {'status': 'queued', 'job_id': job_id}

    thread = threading.Thread(target=_run_yolo_training, args=(job_id, config), daemon=True)
    thread.start()

    with training_lock:
        training_state['thread'] = thread

    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Training started',
        'config': config
    })


@app.route('/api/ai/train/status', methods=['GET'])
def training_status():
    """학습 진행 상태 조회"""
    with training_lock:
        return jsonify({
            'success': True,
            'is_training': training_state['is_training'],
            'progress': training_state['progress']
        })


@app.route('/api/ai/train/stop', methods=['POST'])
def stop_training():
    """학습 중단"""
    with training_lock:
        if not training_state['is_training']:
            return jsonify({
                'success': False,
                'error': 'No training in progress'
            }), 400

        training_state['cancel_requested'] = True

    return jsonify({
        'success': True,
        'message': 'Cancel requested. Training will stop after current epoch.'
    })


@app.route('/api/ai/models', methods=['GET'])
def list_models():
    """학습된 모델 목록"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    runs_dir = os.path.join(script_dir, 'runs')
    models = []

    # runs/ 하위 디렉토리에서 best.pt 찾기
    if os.path.exists(runs_dir):
        for root, dirs, files in os.walk(runs_dir):
            if 'best.pt' in files:
                best_path = os.path.join(root, 'best.pt')
                # 상위 디렉토리에서 args.yaml 읽기
                train_dir = os.path.dirname(os.path.dirname(best_path))
                args_file = os.path.join(train_dir, 'args.yaml')
                info = {
                    'path': best_path,
                    'name': os.path.basename(train_dir),
                    'size_mb': round(os.path.getsize(best_path) / 1024 / 1024, 1),
                    'created': os.path.getmtime(best_path)
                }
                # args.yaml에서 학습 정보 읽기
                if os.path.exists(args_file):
                    try:
                        import yaml
                        with open(args_file) as f:
                            args = yaml.safe_load(f)
                        info['epochs'] = args.get('epochs')
                        info['imgsz'] = args.get('imgsz')
                        info['model'] = args.get('model')
                        info['data'] = args.get('data')
                    except:
                        pass
                models.append(info)

    # pretrained 모델
    pretrained = os.path.join(script_dir, 'yolov8n-seg.pt')
    if os.path.exists(pretrained):
        models.append({
            'path': pretrained,
            'name': 'yolov8n-seg (pretrained)',
            'size_mb': round(os.path.getsize(pretrained) / 1024 / 1024, 1),
            'created': os.path.getmtime(pretrained),
            'is_pretrained': True
        })

    # 현재 활성 모델
    active_model = None
    if yolo_initialized and yolo_model:
        active_model = str(yolo_model.ckpt_path) if hasattr(yolo_model, 'ckpt_path') else 'unknown'

    return jsonify({
        'success': True,
        'models': sorted(models, key=lambda x: x.get('created', 0), reverse=True),
        'active_model': active_model
    })


@app.route('/api/ai/models/activate', methods=['POST'])
def activate_model():
    """학습된 모델을 추론 모델로 전환"""
    global yolo_model, yolo_initialized

    data = request.json or {}
    model_path = data.get('model_path')

    if not model_path:
        return jsonify({'success': False, 'error': 'model_path required'}), 400

    if not os.path.exists(model_path):
        return jsonify({'success': False, 'error': f'Model not found: {model_path}'}), 404

    try:
        # 기존 모델 해제
        yolo_model = None
        yolo_initialized = False
        torch.cuda.empty_cache()

        success = load_yolo_model(model_path)
        if success:
            return jsonify({
                'success': True,
                'message': f'Model activated: {model_path}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to load model'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ai/datasets', methods=['GET'])
def list_datasets():
    """빌드된 YOLO 데이터셋 목록"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    datasets = []

    for entry in os.scandir(script_dir):
        if entry.is_dir() and entry.name.startswith('pipe_dataset'):
            data_yaml = os.path.join(entry.path, 'data.yaml')
            info_json = os.path.join(entry.path, 'dataset_info.json')

            ds = {
                'name': entry.name,
                'path': entry.path,
            }

            if os.path.exists(info_json):
                try:
                    with open(info_json) as f:
                        info = json.load(f)
                    ds.update({
                        'total_frames': info.get('total_frames', 0),
                        'train_count': info.get('train_count', 0),
                        'val_count': info.get('val_count', 0),
                        'test_count': info.get('test_count', 0),
                        'num_classes': info.get('num_classes', 0),
                        'class_names': info.get('class_names', []),
                        'created_at': info.get('created_at', ''),
                    })
                except:
                    pass
            elif os.path.exists(data_yaml):
                # data.yaml에서 기본 정보 추출
                try:
                    import yaml
                    with open(data_yaml) as f:
                        ydata = yaml.safe_load(f)
                    ds['num_classes'] = ydata.get('nc', 0)
                    ds['class_names'] = ydata.get('names', [])
                except:
                    pass

            # 이미지 수 카운트
            train_imgs = os.path.join(entry.path, 'train', 'images')
            if os.path.exists(train_imgs):
                ds.setdefault('train_count', len(os.listdir(train_imgs)))

            datasets.append(ds)

    return jsonify({
        'success': True,
        'datasets': sorted(datasets, key=lambda x: x['name'], reverse=True)
    })
