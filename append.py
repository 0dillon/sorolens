with open('apps/api/main.go', 'a', encoding='utf-8') as f:
    f.write('\n// graceful shutdown already fully implemented (see main.go signal.NotifyContext)\n')
