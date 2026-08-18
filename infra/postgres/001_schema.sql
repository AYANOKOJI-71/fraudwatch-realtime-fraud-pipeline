CREATE TABLE IF NOT EXISTS transaction_events (
  event_id TEXT PRIMARY KEY,
  account_token TEXT NOT NULL,
  amount_usd NUMERIC(12,2) NOT NULL CHECK (amount_usd > 0),
  merchant_category TEXT NOT NULL,
  country CHAR(2) NOT NULL,
  home_country CHAR(2) NOT NULL,
  new_device BOOLEAN NOT NULL DEFAULT FALSE,
  occurred_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS fraud_decisions (
  event_id TEXT PRIMARY KEY REFERENCES transaction_events(event_id),
  action TEXT NOT NULL CHECK (action IN ('allow', 'review', 'block')),
  score SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 100),
  rule_codes JSONB NOT NULL,
  velocity_count_5m INTEGER NOT NULL,
  latency_ms NUMERIC(10,3) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS investigation_cases (
  case_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE REFERENCES transaction_events(event_id),
  status TEXT NOT NULL CHECK (status IN ('open', 'triaged', 'closed')) DEFAULT 'open',
  priority TEXT NOT NULL CHECK (priority IN ('high', 'critical')),
  score SMALLINT NOT NULL,
  rule_codes JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
  sequence BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES transaction_events(event_id),
  action TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
