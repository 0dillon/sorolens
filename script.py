with open('apps/api/internal/handler/subscriptions.go', 'a', encoding='utf-8') as f:
    f.write('''
// ListDeliveries handles GET /api/v1/watchdog/subscriptions/{id}/deliveries.
func (h *Handler) ListDeliveries(w http.ResponseWriter, r *http.Request) {
\tid := chi.URLParam(r, "id")
\t
\tlimit := 50
\toffset := 0
\t
\tdeliveriesStore := h.Store.WebhookDeliveries()
\tdeliveries, err := deliveriesStore.ListBySubscription(r.Context(), id, limit, offset)
\tif err != nil {
\t\th.Logger.Error("list deliveries", "err", err)
\t\twriteError(w, r, http.StatusInternalServerError, CodeInternal, "failed to list deliveries")
\t\treturn
\t}
\t
\twriteJSON(w, http.StatusOK, map[string]any{"deliveries": deliveries})
}
''')
