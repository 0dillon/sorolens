def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('\\', '`')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('apps/api/internal/store/deliveries.go')
fix_file('apps/api/internal/store/subscriptions.go')
