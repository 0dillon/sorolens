with open('services/indexer/internal/watchdog/notifier_test.go', 'r', encoding='utf-16le') as f:
    text = f.read()
text = text.replace('\\', '')
with open('services/indexer/internal/watchdog/notifier_test.go', 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
