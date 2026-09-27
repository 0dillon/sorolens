def insert_mock(filepath, classname, pkg='store'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'WebhookDeliveries()' in content:
        return
        
    func = f"\nfunc (m *{classname}) WebhookDeliveries() {pkg}.WebhookDeliveryStore {{\n\treturn nil\n}}\n"
    if pkg == '':
        func = f"\nfunc (m *{classname}) WebhookDeliveries() WebhookDeliveryStore {{\n\treturn nil\n}}\n"
    
    content += func
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

insert_mock('apps/api/internal/changelog/handler_test.go', 'fakeStore')
insert_mock('apps/api/internal/router/timeout_test.go', 'stuckStore', 'store')
insert_mock('apps/api/internal/store/mock.go', 'MockStore', '')

