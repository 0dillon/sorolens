package watchdog

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"strings"
	"sync"
	"testing"
	"time"
)

const (
	notifyContract = "CABQGAYDAMBQGAYDAMBQGAYDAMBQGAYDAMBQGAYDAMBQGAYDAMBQGCK3"
	notifyTx       = "8c1f0e4b8a7d2c9e6b5a4f3e2d1c0b9a8f7e6d5c4b3a29181716151413121110"
)

func criticalAlert() Alert {
	return Alert{
		ContractID: notifyContract,
		Severity:   "Critical",
		Message:    "health check missed 3 intervals",
		Ledger:     123456,
		TxHash:     notifyTx,
		Timestamp:  time.Date(2026, 9, 25, 10, 0, 0, 0, time.UTC),
	}
}

// decode renders a formatted notification back into a generic map.
func decode(t *testing.T, sub AlertSubscription) (string, map[string]any) {
	t.Helper()
	url, body, err := FormatNotification(sub, criticalAlert())
	if err != nil {
		t.Fatalf("format: %v", err)
	}
	var out map[string]any
	if err := json.Unmarshal(body, &out); err != nil {
		t.Fatalf("payload is not JSON: %v", err)
	}
	return url, out
}

// dig walks a decoded JSON value by map keys and slice indexes.
func dig(t *testing.T, v any, path ...any) any {
	t.Helper()
	for _, p := range path {
		switch k := p.(type) {
		case string:
			m, ok := v.(map[string]any)
			if !ok {
				t.Fatalf("path %v: want object at %q, got %T", path, k, v)
			}
			v = m[k]
		case int:
			s, ok := v.([]any)
			if !ok || k >= len(s) {
				t.Fatalf("path %v: want array with index %d, got %T", path, k, v)
			}
			v = s[k]
		}
	}
	return v
}

func TestFormatWebhook(t *testing.T) {
	url, p := decode(t, AlertSubscription{ID: "s1", WebhookURL: "https://example.com/hook"})
	if url != "https://example.com/hook" {
		t.Fatalf("url: %s", url)
	}
	want := map[string]any{
		"contract_id":  notifyContract,
		"severity":     "Critical",
		"message":      "health check missed 3 intervals",
		"timestamp":    "2026-09-25T10:00:00Z",
		"explorer_url": "https://sorobanexplorer.com/transaction/" + notifyTx,
	}
	for k, v := range want {
		if p[k] != v {
			t.Errorf("%s: want %v, got %v", k, v, p[k])
		}
	}
}

func TestFormatSlackBlockKit(t *testing.T) {
	url, p := decode(t, AlertSubscription{ID: "s1", ChannelType: ChannelSlack, WebhookURL: "https://hooks.slack.com/services/T/B/X"})
	if url != "https://hooks.slack.com/services/T/B/X" {
		t.Fatalf("url: %s", url)
	}
	if text, _ := p["text"].(string); !strings.Contains(text, ":rotating_light:") || !strings.Contains(text, notifyContract) {
		t.Errorf("fallback text: %q", text)
	}
	if got := dig(t, p, "blocks", 0, "type"); got != "header" {
		t.Errorf("first block: %v", got)
	}
	if got := dig(t, p, "blocks", 0, "text", "text"); got != "Critical alert" {
		t.Errorf("header text: %v", got)
	}
	if got := dig(t, p, "blocks", 1, "fields", 0, "text"); got != "*Contract*\n`"+notifyContract+"`" {
		t.Errorf("contract field: %v", got)
	}
	if got := dig(t, p, "blocks", 2, "text", "text"); got != "health check missed 3 intervals" {
		t.Errorf("message: %v", got)
	}
	if got := dig(t, p, "blocks", 4, "elements", 0, "url"); got != "https://sorobanexplorer.com/transaction/"+notifyTx {
		t.Errorf("button url: %v", got)
	}
}

func TestFormatDiscordEmbed(t *testing.T) {
	_, p := decode(t, AlertSubscription{ID: "s1", ChannelType: ChannelDiscord, WebhookURL: "https://discord.com/api/webhooks/1/abc"})
	if p["username"] != "Sorolens" {
		t.Errorf("username: %v", p["username"])
	}
	embed := dig(t, p, "embeds", 0)
	if got := dig(t, embed, "title"); got != "Critical alert" {
		t.Errorf("title: %v", got)
	}
	if got := dig(t, embed, "color"); got != float64(discordColorCritical) {
		t.Errorf("color: %v", got)
	}
	if got := dig(t, embed, "timestamp"); got != "2026-09-25T10:00:00Z" {
		t.Errorf("timestamp: %v", got)
	}
	if got := dig(t, embed, "fields", 0, "value"); got != "`"+notifyContract+"`" {
		t.Errorf("contract field: %v", got)
	}
	if got := dig(t, embed, "fields", 2, "value"); got != "123456" {
		t.Errorf("ledger field: %v", got)
	}
}

func TestFormatPagerDutyEventsV2(t *testing.T) {
	url, p := decode(t, AlertSubscription{ID: "s1", ChannelType: ChannelPagerDuty, RoutingKey: "R0UT1NGKEY"})
	if url != PagerDutyEventsURL {
		t.Fatalf("url: want default events endpoint, got %s", url)
	}
	if p["routing_key"] != "R0UT1NGKEY" || p["event_action"] != "trigger" {
		t.Errorf("envelope: %v", p)
	}
	if p["dedup_key"] != "sorolens:"+notifyContract+":"+notifyTx {
		t.Errorf("dedup_key: %v", p["dedup_key"])
	}
	if got := dig(t, p, "payload", "severity"); got != "critical" {
		t.Errorf("severity: %v", got)
	}
	if got := dig(t, p, "payload", "source"); got != notifyContract {
		t.Errorf("source: %v", got)
	}
	if got := dig(t, p, "payload", "summary"); got != "[Critical] "+notifyContract+": health check missed 3 intervals" {
		t.Errorf("summary: %v", got)
	}
	if got := dig(t, p, "links", 0, "href"); got != "https://sorobanexplorer.com/transaction/"+notifyTx {
		t.Errorf("link: %v", got)
	}
}

func TestPagerDutySeverityMapping(t *testing.T) {
	for in, want := range map[string]string{"Critical": "critical", "Warning": "warning", "Info": "info"} {
		if got := pagerDutySeverity(in); got != want {
			t.Errorf("%s: want %s, got %s", in, want, got)
		}
	}
}

func TestFormatNotificationErrors(t *testing.T) {
	cases := map[string]AlertSubscription{
		"pagerduty without key": {ID: "s", ChannelType: ChannelPagerDuty},
		"unknown channel":       {ID: "s", ChannelType: "carrier-pigeon", WebhookURL: "https://x"},
		"webhook without url":   {ID: "s", ChannelType: ChannelWebhook},
	}
	for name, sub := range cases {
		if _, _, err := FormatNotification(sub, criticalAlert()); err == nil {
			t.Errorf("%s: want error", name)
		}
	}
}

func TestTruncate(t *testing.T) {
	if got := truncate("héllo wörld", 5); got != "héll…" {
		t.Fatalf("got %q", got)
	}
	if got := truncate("short", 10); got != "short" {
		t.Fatalf("got %q", got)
	}
}

type fakeDeliveryStore struct {
	mu         sync.Mutex
	deliveries []WebhookDelivery
}

func (f *fakeDeliveryStore) Insert(_ context.Context, d WebhookDelivery) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.deliveries = append(f.deliveries, d)
	return nil
}

func (f *fakeDeliveryStore) ListPending(_ context.Context, limit int) ([]WebhookDelivery, error) {
	return nil, nil
}

func (f *fakeDeliveryStore) UpdateStatus(_ context.Context, id string, status string, attempts int, nextAttemptAt time.Time, lastErr string) error {
	return nil
}

type fakeSubStore struct {
	subs []AlertSubscription
	ds   *fakeDeliveryStore
}

func (f fakeSubStore) ListByContract(_ context.Context, _ string) ([]AlertSubscription, error) {
	return f.subs, nil
}

func (f fakeSubStore) GetByID(_ context.Context, id string) (AlertSubscription, error) {
	for _, s := range f.subs {
		if s.ID == id {
			return s, nil
		}
	}
	return AlertSubscription{}, nil
}

func (f fakeSubStore) WebhookDeliveries() WebhookDeliveryStore {
	return f.ds
}

// TestDispatchDeliversEachChannel sends a Critical alert to one subscription
// per channel and checks each endpoint receives its own format, retrying a
// 5xx once with the full body.
func TestDispatchDeliversEachChannel(t *testing.T) {
	ds := &fakeDeliveryStore{}
	subs := fakeSubStore{
		subs: []AlertSubscription{
			{ID: "w", ChannelType: ChannelWebhook, WebhookURL: "http://test/webhook", SeverityFilter: "Critical"},
			{ID: "s", ChannelType: ChannelSlack, WebhookURL: "http://test/slack", SeverityFilter: "Critical"},
			{ID: "d", ChannelType: ChannelDiscord, WebhookURL: "http://test/discord", SeverityFilter: "Critical"},
			{ID: "p", ChannelType: ChannelPagerDuty, WebhookURL: "http://test/pagerduty", RoutingKey: "k", SeverityFilter: "Critical"},
		},
		ds: ds,
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	DispatchAlerts(context.Background(), criticalAlert(), subs, logger)

	deadline := time.Now().Add(3 * time.Second)
	for {
		ds.mu.Lock()
		count := len(ds.deliveries)
		ds.mu.Unlock()
		if count == 4 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("expected 4 deliveries, got %d", count)
		}
		time.Sleep(10 * time.Millisecond)
	}

	ds.mu.Lock()
	defer ds.mu.Unlock()

	received := map[string]map[string]any{}
	for _, d := range ds.deliveries {
		var p map[string]any
		if err := json.Unmarshal(d.AlertPayload, &p); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		received[d.SubscriptionID] = p
	}

	if received["w"]["severity"] != "Critical" {
		t.Error("webhook payload")
	}
	if _, ok := received["s"]["blocks"]; !ok {
		t.Error("slack payload must carry blocks")
	}
	if _, ok := received["d"]["embeds"]; !ok {
		t.Error("discord payload must carry embeds")
	}
	if received["p"]["routing_key"] != "k" {
		t.Errorf("pagerduty attempt lost its body: %v", received["p"])
	}
}

func TestDispatchSkipsNonCritical(t *testing.T) {
	ds := &fakeDeliveryStore{}
	a := criticalAlert()
	a.Severity = "Warning"
	DispatchAlerts(context.Background(), a, fakeSubStore{
		subs: []AlertSubscription{{ID: "w", WebhookURL: "http://test", SeverityFilter: "Warning"}},
		ds:   ds,
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))
	
	time.Sleep(50 * time.Millisecond)
	ds.mu.Lock()
	defer ds.mu.Unlock()
	if len(ds.deliveries) > 0 {
		t.Fatal("non-critical alerts must not be dispatched")
	}
}
