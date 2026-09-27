with open('apps/api/main.go', 'r', encoding='utf-8') as f:
    c = f.read()

old_sig = '''	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()'''

new_sig = '''	// Listen for SIGTERM/SIGINT to gracefully stop accepting new connections
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()'''

c = c.replace(old_sig, new_sig)

with open('apps/api/main.go', 'w', encoding='utf-8') as f:
    f.write(c)
