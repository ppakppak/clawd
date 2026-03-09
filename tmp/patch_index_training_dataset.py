from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/index.html')
s = p.read_text()

# 1) showTab: training 탭 초기화 호출 추가
old = """            // 추론 탭 클릭 시 프로젝트 목록 로드
            if (tabName === 'inference') {
                initInferenceTab();
            }
"""
new = """            // 추론 탭 클릭 시 프로젝트 목록 로드
            if (tabName === 'inference') {
                initInferenceTab();
            }

            // 학습 탭 클릭 시 상태 로드
            if (tabName === 'training' && typeof initTrainingTab === 'function') {
                initTrainingTab();
            }
"""
if old not in s:
    raise SystemExit('showTab block not found')
s = s.replace(old, new, 1)

# 2) Training placeholder functions 교체
old_block = """        // ===== Training Tab Functions =====
        function browseDataset() {
            alert('데이터셋 선택 기능은 구현 예정입니다.');
        }

        function startTraining() {
            alert('학습 시작 기능은 구현 예정입니다.');
        }

        function stopTraining() {
            alert('학습 중지 기능은 구현 예정입니다.');
        }

        // ===== Inference Tab Functions =====
"""
new_block = """        // ===== Training Tab Functions =====
        let trainingStatusInterval = null;
        let lastBuiltDatasetPath = null;

        function appendTrainingLog(message, color = '#ccc') {
            const logDiv = document.getElementById('trainingLog');
            if (!logDiv) return;
            const ts = new Date().toLocaleTimeString();
            logDiv.innerHTML += `<div style=\"color:${color};\">[${ts}] ${message}</div>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function setTrainingButtons(isTraining) {
            const startBtn = document.getElementById('startTrainingBtn');
            const stopBtn = document.getElementById('stopTrainingBtn');
            if (startBtn) startBtn.disabled = !!isTraining;
            if (stopBtn) stopBtn.disabled = !isTraining;
        }

        function updateTrainingProgress(percent, text, color = '#28a745') {
            const bar = document.getElementById('trainingProgressBar');
            const textEl = document.getElementById('trainingProgressText');
            if (!bar || !textEl) return;
            const p = Math.max(0, Math.min(100, Number(percent) || 0));
            bar.style.width = `${p}%`;
            bar.style.background = color;
            textEl.textContent = text || `${p.toFixed(1)}%`;
        }

        function ensureTrainingPolling() {
            if (trainingStatusInterval) return;
            trainingStatusInterval = setInterval(() => {
                fetchTrainingStatus(true);
            }, 3000);
        }

        function stopTrainingPolling() {
            if (trainingStatusInterval) {
                clearInterval(trainingStatusInterval);
                trainingStatusInterval = null;
            }
        }

        function useDatasetForTraining(datasetPath) {
            if (!datasetPath) return;
            const input = document.getElementById('trainingDatasetPath');
            if (input) input.value = datasetPath;
            const modelType = document.getElementById('trainingModelType');
            if (modelType) modelType.value = 'yolo';
            appendTrainingLog(`데이터셋 경로 설정: ${datasetPath}`, '#4a9eff');
            showTab('training');
        }

        async function initTrainingTab() {
            const input = document.getElementById('trainingDatasetPath');
            if (input && (!input.value || input.value === 'pipe_dataset') && lastBuiltDatasetPath) {
                input.value = lastBuiltDatasetPath;
            }
            await fetchTrainingStatus(true);
        }

        function browseDataset() {
            const current = document.getElementById('trainingDatasetPath').value || lastBuiltDatasetPath || '/home/intu/projects/pipe-inspector-staging/gpu-server';
            const picked = prompt('학습용 데이터셋 경로를 입력하세요', current);
            if (picked && picked.trim()) {
                document.getElementById('trainingDatasetPath').value = picked.trim();
            }
        }

        async function startTraining() {
            const modelType = document.getElementById('trainingModelType').value;
            if (modelType !== 'yolo') {
                alert('현재는 YOLO Segmentation 학습만 지원합니다.');
                return;
            }

            const datasetPath = document.getElementById('trainingDatasetPath').value.trim();
            const projectName = document.getElementById('trainingOutputPath').value.trim() || 'pipe_defect';
            const epochs = parseInt(document.getElementById('trainingEpochs').value, 10) || 100;
            const batchSize = parseInt(document.getElementById('trainingBatchSize').value, 10) || 8;
            const lr0 = parseFloat(document.getElementById('trainingLR').value) || 0.01;

            if (!datasetPath) {
                alert('데이터셋 경로를 입력하세요.');
                return;
            }

            setTrainingButtons(true);
            appendTrainingLog('학습 시작 요청 전송...', '#ffa500');
            updateTrainingProgress(0, '요청 중...', '#4a9eff');

            try {
                const response = await authFetch('/api/ai/train', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset_path: datasetPath,
                        model_size: 'n',
                        epochs: epochs,
                        batch_size: batchSize,
                        lr0: lr0,
                        img_size: 640,
                        project_name: projectName,
                    })
                });
                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || '학습 시작 실패');
                }

                appendTrainingLog(`✅ 학습 시작됨 (job: ${data.job_id})`, '#28a745');
                ensureTrainingPolling();
                await fetchTrainingStatus(true);
            } catch (error) {
                setTrainingButtons(false);
                appendTrainingLog(`❌ 학습 시작 실패: ${error.message}`, '#ff6b6b');
                updateTrainingProgress(0, '시작 실패', '#ff6b6b');
            }
        }

        async function fetchTrainingStatus(silent = false) {
            try {
                const response = await authFetch('/api/ai/train/status');
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.error || '상태 조회 실패');
                }

                const isTraining = !!data.is_training;
                const progress = data.progress || {};
                const status = progress.status || (isTraining ? 'training' : 'idle');

                if (status === 'queued') {
                    updateTrainingProgress(0, '대기 중...', '#4a9eff');
                    setTrainingButtons(true);
                    ensureTrainingPolling();
                } else if (status === 'starting') {
                    updateTrainingProgress(1, '초기화 중...', '#4a9eff');
                    setTrainingButtons(true);
                    ensureTrainingPolling();
                } else if (status === 'training') {
                    const percent = progress.percent || (progress.epoch && progress.total_epochs ? (progress.epoch / progress.total_epochs) * 100 : 0);
                    updateTrainingProgress(percent, `${progress.epoch || 0}/${progress.total_epochs || 0} epoch`, '#28a745');
                    setTrainingButtons(true);
                    ensureTrainingPolling();
                } else if (status === 'completed') {
                    updateTrainingProgress(100, '완료', '#28a745');
                    setTrainingButtons(false);
                    stopTrainingPolling();
                    if (!silent) {
                        appendTrainingLog('✅ 학습 완료', '#28a745');
                        if (progress.best_model) appendTrainingLog(`best.pt: ${progress.best_model}`, '#4a9eff');
                    }
                } else if (status === 'cancelled') {
                    updateTrainingProgress(progress.percent || 0, '중단됨', '#ff6b6b');
                    setTrainingButtons(false);
                    stopTrainingPolling();
                    if (!silent) appendTrainingLog('⚠️ 학습 중단됨', '#ffa500');
                } else if (status === 'error') {
                    updateTrainingProgress(progress.percent || 0, '오류', '#ff6b6b');
                    setTrainingButtons(false);
                    stopTrainingPolling();
                    if (!silent) appendTrainingLog(`❌ 오류: ${progress.error || 'unknown'}`, '#ff6b6b');
                } else {
                    setTrainingButtons(isTraining);
                    if (!isTraining) stopTrainingPolling();
                }
            } catch (error) {
                if (!silent) appendTrainingLog(`상태 조회 실패: ${error.message}`, '#ff6b6b');
            }
        }

        async function stopTraining() {
            try {
                appendTrainingLog('중단 요청 전송...', '#ffa500');
                const response = await authFetch('/api/ai/train/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.error || '중단 요청 실패');
                }
                appendTrainingLog('⏹ 중단 요청 완료 (현재 epoch 종료 후 반영)', '#ffa500');
                ensureTrainingPolling();
            } catch (error) {
                appendTrainingLog(`❌ 중단 실패: ${error.message}`, '#ff6b6b');
            }
        }

        // ===== Inference Tab Functions =====
"""
if old_block not in s:
    raise SystemExit('training placeholder block not found')
s = s.replace(old_block, new_block, 1)

# 3) showDatasetResult 성공 시 학습 탭 연동
old_line = """                content.innerHTML = `
"""
# first occurrence is success block in showDatasetResult
idx = s.find(old_line)
if idx == -1:
    raise SystemExit('showDatasetResult content block start not found')

# Insert lastBuiltDatasetPath assignment right before content.innerHTML in success path
insert_point = idx
s = s[:insert_point] + "                lastBuiltDatasetPath = result.outputDir;\n" + s[insert_point:]

# Add quick button in success card by appending after template assignment block
needle = """                `;

                // 패널로 스크롤
"""
replace = """                `;

                const escapedOutput = String(result.outputDir || '').replace(/\\/g, '\\\\').replace(/'/g, "\\\\'");
                content.innerHTML += `
                    <div style=\"grid-column: 1 / -1; background: #0d1f0d; padding: 15px; border-radius: 6px; text-align:center;\">
                        <button onclick=\"useDatasetForTraining('${escapedOutput}')\" style=\"padding:10px 20px; background:#4a9eff; border:none; color:white; border-radius:6px; cursor:pointer; font-weight:bold;\">🚀 이 데이터셋으로 학습하기</button>
                    </div>
                `;

                // 패널로 스크롤
"""
if needle not in s:
    raise SystemExit('showDatasetResult tail not found')
s = s.replace(needle, replace, 1)

# 4) 클래스 선택 Step에 2클래스 프리셋 버튼 추가
step2_buttons_old = """                        <div style=\"display: flex; gap: 10px; margin-top: 15px; justify-content: center;\">
                            <button onclick=\"selectAllClasses()\" style=\"padding: 8px 20px; background: #9b59b6; border: none; color: white; border-radius: 6px; cursor: pointer;\">전체 선택</button>
                            <button onclick=\"deselectAllClasses()\" style=\"padding: 8px 20px; background: #555; border: none; color: white; border-radius: 6px; cursor: pointer;\">전체 해제</button>
                        </div>
"""
step2_buttons_new = """                        <div style=\"display: flex; gap: 10px; margin-top: 15px; justify-content: center; flex-wrap: wrap;\">
                            <button onclick=\"selectAllClasses()\" style=\"padding: 8px 20px; background: #9b59b6; border: none; color: white; border-radius: 6px; cursor: pointer;\">전체 선택</button>
                            <button onclick=\"deselectAllClasses()\" style=\"padding: 8px 20px; background: #555; border: none; color: white; border-radius: 6px; cursor: pointer;\">전체 해제</button>
                            <button onclick=\"selectCorrosion2Preset()\" style=\"padding: 8px 20px; background: #e67e22; border: none; color: white; border-radius: 6px; cursor: pointer; font-weight: bold;\">🧪 부식 2클래스(결절/녹) 프리셋</button>
                        </div>
"""
if step2_buttons_old not in s:
    raise SystemExit('step2 button block not found')
s = s.replace(step2_buttons_old, step2_buttons_new, 1)

# 5) 프리셋 함수 추가 (toggleDatasetClass 앞)
anchor_fn = """        // Toggle class selection
        function toggleDatasetClass(className) {
"""
insert_fn = """        function selectCorrosion2Preset() {
            const target = ['부식(결절)', '부식(녹)'];
            const available = [];

            // 현재 표시된 클래스 목록에서 사용 가능 여부 확인
            const classLabels = document.querySelectorAll('#datasetClassFilter label span:first-of-type');
            classLabels.forEach(el => available.push(el.textContent.split(' (')[0].trim()));

            const missing = target.filter(c => !available.includes(c));
            if (missing.length > 0) {
                alert('프리셋 클래스 일부를 찾지 못했습니다: ' + missing.join(', '));
            }

            datasetSelectedClasses.clear();
            target.forEach(c => {
                if (available.includes(c)) datasetSelectedClasses.add(c);
            });

            updateDatasetClassFilter();
            updateDatasetVideosList();
            updateDatasetStats();
            updateBuildSummary();

            const outEl = document.getElementById('datasetOutputPath');
            if (outEl) outEl.value = 'pipe_dataset_corrosion2';

            if (datasetSelectedClasses.size > 0) {
                alert(`프리셋 적용 완료: ${Array.from(datasetSelectedClasses).join(', ')}`);
            }
        }

        // Toggle class selection
        function toggleDatasetClass(className) {
"""
if anchor_fn not in s:
    raise SystemExit('toggleDatasetClass anchor not found')
s = s.replace(anchor_fn, insert_fn, 1)

p.write_text(s)
print('patched index.html')
