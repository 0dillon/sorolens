package store

import (
	"context"
	"time"
)

type webhookDeliveryStore struct {
	store *postgresStore
}

func (s *webhookDeliveryStore) Insert(ctx context.Context, d WebhookDelivery) error {
	_, err := s.store.pool.Exec(ctx, `
		INSERT INTO webhook_deliveries
			(id, subscription_id, alert_payload, status, attempts, max_attempts, next_attempt_at, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`, d.ID, d.SubscriptionID, d.AlertPayload, d.Status, d.Attempts, d.MaxAttempts, d.NextAttemptAt, d.CreatedAt, d.UpdatedAt)
	return err
}

func (s *webhookDeliveryStore) ListPending(ctx context.Context, limit int) ([]WebhookDelivery, error) {
	rows, err := s.store.pool.Query(ctx, `
		SELECT id, subscription_id, alert_payload, status, attempts, max_attempts, next_attempt_at, last_error, created_at, updated_at
		FROM webhook_deliveries
		WHERE status = 'pending' AND next_attempt_at <= NOW()
		ORDER BY next_attempt_at ASC
		LIMIT $1
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []WebhookDelivery
	for rows.Next() {
		var d WebhookDelivery
		var lastErr *string
		if err := rows.Scan(&d.ID, &d.SubscriptionID, &d.AlertPayload, &d.Status, &d.Attempts, &d.MaxAttempts, &d.NextAttemptAt, &lastErr, &d.CreatedAt, &d.UpdatedAt); err != nil {
			return nil, err
		}
		if lastErr != nil {
			d.LastError = *lastErr
		}
		out = append(out, d)
	}
	return out, rows.Err()
}

func (s *webhookDeliveryStore) UpdateStatus(ctx context.Context, id string, status string, attempts int, nextAttemptAt time.Time, lastErr string) error {
	// First update the delivery
	var errStr *string
	if lastErr != "" {
		errStr = &lastErr
	}
	
	tx, err := s.store.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	_, err = tx.Exec(ctx, `
		UPDATE webhook_deliveries
		SET status = $1, attempts = $2, next_attempt_at = $3, last_error = $4, updated_at = NOW()
		WHERE id = $5
	`, status, attempts, nextAttemptAt, errStr, id)
	if err != nil {
		return err
	}

	// Then update the subscription's last_delivery_* fields.
	// We need the subscription ID first.
	var subID string
	err = tx.QueryRow(ctx, "SELECT subscription_id FROM webhook_deliveries WHERE id = $1", id).Scan(&subID)
	if err != nil {
		return err
	}

	_, err = tx.Exec(ctx, `
		UPDATE alert_subscriptions
		SET last_delivery_status = $1, last_delivery_at = NOW()
		WHERE id = $2
	`, status, subID)
	if err != nil {
		return err
	}

	return tx.Commit(ctx)
}

func (s *webhookDeliveryStore) ListBySubscription(ctx context.Context, subID string, limit int, offset int) ([]WebhookDelivery, error) {
	rows, err := s.store.pool.Query(ctx, `
		SELECT id, subscription_id, alert_payload, status, attempts, max_attempts, next_attempt_at, last_error, created_at, updated_at
		FROM webhook_deliveries
		WHERE subscription_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`, subID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []WebhookDelivery
	for rows.Next() {
		var d WebhookDelivery
		var lastErr *string
		if err := rows.Scan(&d.ID, &d.SubscriptionID, &d.AlertPayload, &d.Status, &d.Attempts, &d.MaxAttempts, &d.NextAttemptAt, &lastErr, &d.CreatedAt, &d.UpdatedAt); err != nil {
			return nil, err
		}
		if lastErr != nil {
			d.LastError = *lastErr
		}
		out = append(out, d)
	}
	return out, rows.Err()
}

func (s *postgresStore) WebhookDeliveries() WebhookDeliveryStore {
	return &webhookDeliveryStore{store: s}
}
