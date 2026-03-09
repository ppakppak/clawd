from pathlib import Path
p = Path('/home/intu/projects/pipe-inspector-staging/index.html')
lines = p.read_text().splitlines()
needle = 'const escapedOutput = String(result.outputDir ||'
repl = "                const escapedOutput = String(result.outputDir || '').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, \"\\\\'\");"
changed = False
for i, l in enumerate(lines):
    if needle in l:
        lines[i] = repl
        changed = True
        break
if not changed:
    raise SystemExit('line not found')
p.write_text('\n'.join(lines) + '\n')
print('fixed quote escaping')
