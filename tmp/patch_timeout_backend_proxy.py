from pathlib import Path
p = Path('/home/intu/projects/pipe-inspector-staging/backend_proxy.py')
s = p.read_text()
old = "timeout = 600 if is_dataset_build else 30  # 10분 vs 30초"
new = "timeout = 3600 if is_dataset_build else 30  # 데이터셋 빌드 1시간, 일반 30초"
if old not in s:
    raise SystemExit('timeout line not found')
s = s.replace(old, new, 1)
p.write_text(s)
print('timeout patched')
