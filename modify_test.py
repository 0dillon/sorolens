import re

with open('services/indexer/internal/watchdog/notifier_test.go', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace fakeSubStore definition
fake_store_old = '''type fakeSubStore struct{ subs []AlertSubscription }

func (f fakeSubStore) ListByContract(_ context.Context, _ string) ([]AlertSubscription, error) {
	return f.subs, nil
}'''

fake_store_new = '''type fakeDeliveryStore struct {
	mu         sync.Mutex
	deliveries []WebhookDelivery
}

func (f *fakeDeliveryStore) Insert(_ context.Context, d WebhookDelivery) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.deliveries = append(f.deliveries, d)
	return nil
}

type fakeSubStore struct {
	subs []AlertSubscription
	ds   *fakeDeliveryStore
}

func (f fakeSubStore) ListByContract(_ context.Context, _ string) ([]AlertSubscription, error) {
	return f.subs, nil
}

func (f fakeSubStore) WebhookDeliveries() WebhookDeliveryStore {
	return f.ds
}'''

text = text.replace(fake_store_old, fake_store_new)

# Replace TestDispatchDeliversEachChannel
test_old = '''func TestDispatchDeliversEachChannel(t *testing.T) {
	var (
		mu       sync.Mutex
		received = map[string][]map[string]any{}
		failed   bool
	)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		var p map[string]any
		if err := json.Unmarshal(b, &p); err != nil {
			t.Errorf("%s: body is not JSON (%q)", r.URL.Path, b)
		}
		mu.Lock()
		received[r.URL.Path] = append(received[r.URL.Path], p)
		// The first PagerDuty delivery fails with a 5xx to exercise retry.
		fail := r.URL.Path == "/pagerduty" && !failed
		if fail {
			failed = true
		}
		mu.Unlock()
		if fail {
			w.WriteHeader(http.StatusBadGateway)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	subs := fakeSubStore{subs: []AlertSubscription{
		{ID: "w", ChannelType: ChannelWebhook, WebhookURL: srv.URL + "/webhook", SeverityFilter: "Critical"},
		{ID: "s", ChannelType: ChannelSlack, WebhookURL: srv.URL + "/slack", SeverityFilter: "Critical"},
		{ID: "d", ChannelType: ChannelDiscord, WebhookURL: srv.URL + "/discord", SeverityFilter: "Critical"},
		{ID: "p", ChannelType: ChannelPagerDuty, WebhookURL: srv.URL + "/pagerduty", RoutingKey: "k", SeverityFilter: "Critical"},
	}}
	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelError + 4}))
	DispatchAlerts(context.Background(), criticalAlert(), subs, logger)

	deadline := time.Now().Add(3 * time.Second)
	for {
		mu.Lock()
		done := len(received["/webhook"]) == 1 && len(received["/slack"]) == 1 &&
			len(received["/discord"]) == 1 && len(received["/pagerduty"]) == 2
		mu.Unlock()
		if done {
			break
		}
		if time.Now().After(deadline) {
			mu.Lock()
			defer mu.Unlock()
			t.Fatalf("deliveries incomplete: %v", received)
		}
		time.Sleep(10 * time.Millisecond)
	}

	mu.Lock()
	defer mu.Unlock()
	if received["/webhook"][0]["severity"] != "Critical" {
		t.Error("webhook payload")
	}
	if _, ok := received["/slack"][0]["blocks"]; !ok {
		t.Error("slack payload must carry blocks")
	}
	if _, ok := received["/discord"][0]["embeds"]; !ok {
		t.Error("discord payload must carry embeds")
	}
	for i, p := range received["/pagerduty"] {
		if p["routing_key"] != "k" {
			t.Errorf("pagerduty attempt %d lost its body: %v", i+1, p)
		}
	}
}'''

test_new = '''func TestDispatchDeliversEachChannel(t *testing.T) {
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
}'''

text = text.replace(test_old, test_new)


# Replace TestDispatchSkipsNonCritical
skip_old = '''func TestDispatchSkipsNonCritical(t *testing.T) {
	called := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
	defer srv.Close()
	a := criticalAlert()
	a.Severity = "Warning"
	DispatchAlerts(context.Background(), a, fakeSubStore{subs: []AlertSubscription{{ID: "w", WebhookURL: srv.URL, SeverityFilter: "Warning"}}},
		slog.New(slog.NewTextHandler(io.Discard, nil)))
	time.Sleep(50 * time.Millisecond)
	if called {
		t.Fatal("non-critical alerts must not be dispatched")
	}
}'''

skip_new = '''func TestDispatchSkipsNonCritical(t *testing.T) {
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
}'''

text = text.replace(skip_old, skip_new)

with open('services/indexer/internal/watchdog/notifier_test.go', 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
