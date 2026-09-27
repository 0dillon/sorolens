with open('apps/api/main.go', 'r', encoding='utf-8') as f:
    c = f.read()

# I will replace the shutdown logic with a slightly refactored version
old_shutdown = '''	<-ctx.Done()
	logger.Info("shutting down")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Error("shutdown", "err", err)
	}'''

new_shutdown = '''	<-ctx.Done()
	logger.Info("shutting down on SIGTERM/SIGINT, draining in-flight requests")

	// Drain in-flight requests with a 30s timeout
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Error("shutdown error", "err", err)
	}'''

c = c.replace(old_shutdown, new_shutdown)
c = c.replace('\n// graceful shutdown already fully implemented (see main.go signal.NotifyContext)\n', '')

with open('apps/api/main.go', 'w', encoding='utf-8') as f:
    f.write(c)
