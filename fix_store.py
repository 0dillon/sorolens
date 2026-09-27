with open('apps/api/internal/store/store.go', 'r', encoding='utf-8') as f:
    content = f.read()

if '"time"' not in content:
    content = content.replace('"context"', '"context"\n\t"time"')
    with open('apps/api/internal/store/store.go', 'w', encoding='utf-8') as f:
        f.write(content)
