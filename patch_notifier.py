import re

with open('services/indexer/internal/watchdog/notifier.go', 'r', encoding='utf-8') as f:
    text = f.read()

# Add GetByID to AlertSubscriptionStore
text = text.replace(
'''type AlertSubscriptionStore interface {
	ListByContract(ctx context.Context, contractID string) ([]AlertSubscription, error)
}''',
'''type AlertSubscriptionStore interface {
	ListByContract(ctx context.Context, contractID string) ([]AlertSubscription, error)
	GetByID(ctx context.Context, id string) (AlertSubscription, error)
	WebhookDeliveries() WebhookDeliveryStore
}'''
)

# Add WebhookDelivery and WebhookDeliveryStore
text = text.replace(
'''// AlertSubscription is the local mirror of the store model.''',
'''// WebhookDelivery is the local mirror of the store model.
type WebhookDelivery struct {
	ID             string
	SubscriptionID string
	AlertPayload   []byte
	Status         string
	Attempts       int
	MaxAttempts    int
	NextAttemptAt  time.Time
	LastError      string
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

// WebhookDeliveryStore is the local interface for delivery storage.
type WebhookDeliveryStore interface {
	Insert(ctx context.Context, d WebhookDelivery) error
}

// AlertSubscription is the local mirror of the store model.'''
)

# Modify DispatchAlerts to pass delivery store
text = text.replace(
'''		go deliver(ctx, sub, alert, logger)''',
'''		go deliver(ctx, sub, alert, subStore.WebhookDeliveries(), logger)'''
)

# Replace deliver function completely
old_deliver = '''// deliver sends one notification, retrying once on a 5xx. Each attempt
// builds a fresh request so the body is re-sent in full.
func deliver(ctx context.Context, sub AlertSubscription, alert Alert, logger *slog.Logger) {
	url, body, err := FormatNotification(sub, alert)
	if err != nil {
		logger.Error("dispatch alerts: format", "err", err, "subscription_id", sub.ID, "channel", sub.ChannelType)
		return
	}
	for attempt := 1; attempt <= 2; attempt++ {
		status, err := post(ctx, url, body)
		switch {
		case err != nil:
			logger.Error("dispatch alerts: request failed", "err", err, "subscription_id", sub.ID, "attempt", attempt)
			return
		case status >= 500:
			logger.Error("dispatch alerts: server error", "status", status, "subscription_id", sub.ID, "attempt", attempt)
			continue
		case status >= 400:
			logger.Error("dispatch alerts: client error", "status", status, "subscription_id", sub.ID)
		}
		return
	}
}'''

new_deliver = '''func deliver(ctx context.Context, sub AlertSubscription, alert Alert, deliveryStore WebhookDeliveryStore, logger *slog.Logger) {
	_, body, err := FormatNotification(sub, alert)
	if err != nil {
		logger.Error("dispatch alerts: format", "err", err, "subscription_id", sub.ID, "channel", sub.ChannelType)
		return
	}
	
	err = deliveryStore.Insert(ctx, WebhookDelivery{
		SubscriptionID: sub.ID,
		AlertPayload:   body,
		Status:         "pending",
		Attempts:       0,
		MaxAttempts:    5,
		NextAttemptAt:  time.Now(),
		CreatedAt:      time.Now(),
		UpdatedAt:      time.Now(),
	})
	
	if err != nil {
		logger.Error("dispatch alerts: failed to insert webhook delivery", "err", err, "subscription_id", sub.ID)
	}
}'''

text = text.replace(old_deliver, new_deliver)

with open('services/indexer/internal/watchdog/notifier.go', 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
