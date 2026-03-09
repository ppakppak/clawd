from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/backend_proxy.py')
s = p.read_text()

old = """        # GPU 서버에 빌드 요청
        gpu_response, status_code = forward_to_gpu('/api/dataset/build_yolo', method='POST', json=build_request)

        if status_code == 200 and gpu_response.get('success'):
"""
new = """        # GPU 서버에 빌드 요청 (클래스 필터/ID 재매핑 지원 버전)
        gpu_response, status_code = forward_to_gpu('/api/dataset/build_yolo_filtered', method='POST', json=build_request)

        if status_code == 200 and gpu_response.get('success'):
"""

idx = s.find(old)
if idx == -1:
    raise SystemExit('target snippet not found (first)')
idx2 = s.find(old, idx + 1)
if idx2 == -1:
    raise SystemExit('target snippet not found (second)')
s = s[:idx2] + new + s[idx2 + len(old):]

anchor = """@app.route('/api/ai/inference_box', methods=['POST'])
def run_inference_box():
    \"\"\"박스 영역 AI 추론 실행\"\"\"
    data, status_code = forward_to_gpu('/api/ai/inference_box', method='POST', json=request.json)
    return jsonify(data), status_code


@app.route('/api/export/dataset', methods=['POST'])
def export_dataset():
"""

insert = """@app.route('/api/ai/inference_box', methods=['POST'])
def run_inference_box():
    \"\"\"박스 영역 AI 추론 실행\"\"\"
    data, status_code = forward_to_gpu('/api/ai/inference_box', method='POST', json=request.json)
    return jsonify(data), status_code


@app.route('/api/ai/train', methods=['POST'])
@require_auth
def ai_train_start():
    \"\"\"YOLO 학습 시작 (GPU 서버 프록시)\"\"\"
    data, status_code = forward_to_gpu('/api/ai/train', method='POST', json=request.json)
    return jsonify(data), status_code


@app.route('/api/ai/train/status', methods=['GET'])
@require_auth
def ai_train_status():
    \"\"\"YOLO 학습 상태 조회 (GPU 서버 프록시)\"\"\"
    data, status_code = forward_to_gpu('/api/ai/train/status', method='GET')
    return jsonify(data), status_code


@app.route('/api/ai/train/stop', methods=['POST'])
@require_auth
def ai_train_stop():
    \"\"\"YOLO 학습 중단 요청 (GPU 서버 프록시)\"\"\"
    data, status_code = forward_to_gpu('/api/ai/train/stop', method='POST', json=request.json)
    return jsonify(data), status_code


@app.route('/api/ai/models', methods=['GET'])
@require_auth
def ai_models():
    \"\"\"학습된 모델 목록 (GPU 서버 프록시)\"\"\"
    data, status_code = forward_to_gpu('/api/ai/models', method='GET')
    return jsonify(data), status_code


@app.route('/api/export/dataset', methods=['POST'])
def export_dataset():
"""

if anchor not in s:
    raise SystemExit('anchor for train routes not found')

s = s.replace(anchor, insert, 1)

p.write_text(s)
print('patched backend_proxy.py')
