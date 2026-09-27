package watchdog

import (
	"bytes"
	"context"
	"log/slog"
	"math"
	"net/http"
	"time"
)

// RetryWorkerConfig configures the retry worker.
type RetryWorkerConfig struct {
	PollInterval time.Duration
	BaseDelay    time.Duration
}

// RetryWorker polls the webhook_deliveries table and retries pending deliveries.
type RetryWorker struct {
	subStore AlertSubscriptionStore
	logger   *slog.Logger
	config   RetryWorkerConfig
}

func NewRetryWorker(subStore AlertSubscriptionStore, logger *slog.Logger, config RetryWorkerConfig) *RetryWorker {
	if config.PollInterval == 0 {
		config.PollInterval = 10 * time.Second
	}
	if config.BaseDelay == 0 {
		config.BaseDelay = 1 * time.Minute
	}
	return &RetryWorker{
		subStore: subStore,
		logger:   logger,
		config:   config,
	}
}

func (w *RetryWorker) Run(ctx context.Context) {
	ticker := time.NewTicker(w.config.PollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			w.processBatch(ctx)
		}
	}
}

func (w *RetryWorker) processBatch(ctx context.Context) {
	deliveriesStore := w.subStore.WebhookDeliveries()
	deliveries, err := deliveriesStore.ListPending(ctx, 50)
	if err != nil {
		w.logger.Error("failed to list pending deliveries", "error", err)
		return
	}

	for _, d := range deliveries {
		sub, err := w.subStore.GetByID(ctx, d.SubscriptionID)
		if err != nil {
			w.logger.Error("failed to get subscription", "subscription_id", d.SubscriptionID, "error", err)
			continue
		}

		url := sub.WebhookURL
		if sub.ChannelType == ChannelPagerDuty && url == "" {
			url = PagerDutyEventsURL
		}

		req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(d.AlertPayload))
		if err != nil {
			w.logger.Error("failed to create request", "error", err)
			continue
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := http.DefaultClient.Do(req)
		
		d.Attempts++
		
		var lastErr string
		if err != nil {
			lastErr = err.Error()
		} else {
			resp.Body.Close()
			if resp.StatusCode >= 200 && resp.StatusCode < 300 {
				d.Status = "delivered"
			} else {
				lastErr = resp.Status
			}
		}

		if d.Status != "delivered" {
			if d.Attempts >= d.MaxAttempts {
				d.Status = "failed"
			} else {
				d.NextAttemptAt = time.Now().Add(w.config.BaseDelay * time.Duration(math.Pow(2, float64(d.Attempts-1))))
			}
		}

		err = deliveriesStore.UpdateStatus(ctx, d.ID, d.Status, d.Attempts, d.NextAttemptAt, lastErr)
		if err != nil {
			w.logger.Error("failed to update delivery status", "delivery_id", d.ID, "error", err)
		}
	}
}
