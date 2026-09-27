with open('apps/api/internal/store/store.go', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'context' in line and 'time' in line:
        lines[i] = '\t\"context\"\n\t\"time\"\n'
    elif '\
' in line:
        lines[i] = line.replace('\
', '\n')

with open('apps/api/internal/store/store.go', 'w', encoding='utf-8') as f:
    f.writelines(lines)
