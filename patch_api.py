#!/usr/bin/env python3
"""Patch staging api.py to add training endpoints"""
import re

# Read original api.py
with open('/home/intu/projects/pipe-inspector-staging/gpu-server/api.py', 'r') as f:
    content = f.read()

# Read patch code
with open('/tmp/train_api_patch.py', 'r') as f:
    patch = f.read()

# Remove the docstring at top of patch
patch = re.sub(r'^""".*?"""\n', '', patch, flags=re.DOTALL)

# Find insertion point: before 'if __name__'
marker = "if __name__ == '__main__':"
idx = content.rfind(marker)
if idx == -1:
    print('ERROR: could not find __main__ marker')
    exit(1)

new_content = content[:idx] + patch + '\n\n' + content[idx:]

with open('/home/intu/projects/pipe-inspector-staging/gpu-server/api.py', 'w') as f:
    f.write(new_content)

print(f'PATCHED: inserted {len(patch)} chars before __main__')
print(f'New total lines: {new_content.count(chr(10))}')
