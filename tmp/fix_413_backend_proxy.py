from pathlib import Path

p = Path('/home/intu/projects/pipe-inspector-staging/backend_proxy.py')
s = p.read_text()

start_marker = "        # 각 프로젝트에서 어노테이션 수집\n"
end_marker = "        # GPU 서버로 전달하여 실제 빌드 수행\n"

start = s.find(start_marker)
if start == -1:
    raise SystemExit('start marker not found')
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit('end marker not found')

replacement = """        # 대용량 JSON 전송(413) 방지를 위해\n        # GPU 서버에서 프로젝트 디렉토리를 직접 스캔해 어노테이션을 로드하도록 전달\n        logger.info('[DATASET BUILD-MULTI] Using compact request mode (projects + classes only)')\n\n"""

s = s[:start] + replacement + s[end:]

# Replace build_request payload in build-multi route
old_payload = """        build_request = {\n            'annotations_data': annotations_data,\n            'classes': classes,\n            'output_dir': output_dir,\n            'split_ratio': split_ratio,\n            'format': format_type,\n            'base_projects_dir': str(BASE_PROJECTS_DIR)\n        }\n"""
new_payload = """        build_request = {\n            'projects': projects,\n            'classes': classes,\n            'output_dir': output_dir,\n            'split_ratio': split_ratio,\n            'format': format_type,\n            'base_projects_dir': str(BASE_PROJECTS_DIR)\n        }\n"""

if old_payload not in s:
    raise SystemExit('build_request payload block not found')
s = s.replace(old_payload, new_payload, 1)

p.write_text(s)
print('patched backend_proxy.py for compact build-multi payload')
