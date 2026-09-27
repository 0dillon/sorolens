import re
with open('apps/api/internal/store/models.go', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace json:"..." with `json:"..."` for WebhookDelivery struct
content = re.sub(r'(\s+)json:"([^"]+)"', r'\1`json:"\2"`', content)

with open('apps/api/internal/store/models.go', 'w', encoding='utf-8') as f:
    f.write(content)
