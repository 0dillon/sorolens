with open('apps/api/internal/handler/v2_test.go', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('true,`n\t\t"GET /api/v1/watchdog/subscriptions/{id}/deliveries": true,', 'true,\n\t\t"GET /api/v1/watchdog/subscriptions/{id}/deliveries": true,')
with open('apps/api/internal/handler/v2_test.go', 'w', encoding='utf-8') as f:
    f.write(content)
