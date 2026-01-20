# Observability (Metrics, Tracing, SLO/Alerts)

This project ships a lightweight, local-first observability setup:
- Metrics via `django-prometheus` at `/metrics`
- Tracing via OpenTelemetry (console by default, OTLP optional)
- Prometheus alert rules for core APIs and Celery tasks

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Metrics (/metrics)

Enabled by default in Django via `django-prometheus`.

Access control (recommended for prod):
- `METRICS_ALLOW_ALL` (default: `True` in DEBUG)
- `METRICS_ALLOWED_IPS` (comma-separated)
- `METRICS_TOKEN` (Bearer token or `?token=` query)

Example:
```bash
set METRICS_ALLOW_ALL=false
set METRICS_ALLOWED_IPS=127.0.0.1
set METRICS_TOKEN=local-token
```

### Verify metrics locally
1. Start Django:
   ```bash
   python manage.py runserver
   ```
2. Visit `http://localhost:8000/metrics`
3. Call a few endpoints:
   - `http://localhost:8000/core/login/`
   - `http://localhost:8000/store/shops/`
   - `http://localhost:8000/finance/records/`
4. Refresh `/metrics`, you should see counters and latency histograms increase.

Celery metrics (optional):
```bash
set CELERY_METRICS_PORT=9101
celery -A config worker -l info
```
Scrape `http://localhost:9101/metrics` for task metrics.

## 3) Tracing (OpenTelemetry)

Enable tracing via env:
```bash
set OTEL_ENABLED=true
set OTEL_SERVICE_NAME=store-management
set OTEL_ENVIRONMENT=development
```

Default exporter: console (spans printed to logs).

To export to an OTLP endpoint (local collector, etc.):
```bash
set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

### Verify tracing locally
1. Set `OTEL_ENABLED=true`
2. Start Django
3. Call any HTTP endpoint
4. Observe spans printed in console logs (or sent to OTLP endpoint)

If Celery is running, spans are emitted for task execution as well.

## 4) SLOs and Prometheus alert rules

Core API scope (MVP):
- Login: `apps.core.views.LoginView`
- Shop list: `apps.store.views.ShopListView`
- Contract list: `apps.store.views.ContractListView`
- Finance list: `apps.finance.views.FinanceListView`
- Finance pay: `apps.finance.views.FinancePayView`

Minimal SLOs (recommendation):
- Availability: success rate >= 99% (5xx < 1%)
- Latency: p95 < 1s for core APIs
- Task failure rate < 5%

Alert rules file: `ops/alert_rules.yml`

Note: `django-prometheus` uses the `view` label. If your deployment exposes
`handler` or a different label, update the rules accordingly.

### Prometheus config snippet
```yaml
scrape_configs:
  - job_name: store-management
    metrics_path: /metrics
    static_configs:
      - targets: ['127.0.0.1:8000']
  - job_name: store-management-celery
    metrics_path: /metrics
    static_configs:
      - targets: ['127.0.0.1:9101']

rule_files:
  - ops/alert_rules.yml
```

## 5) Grafana panel suggestions (MVP)

Recommended panels:
- HTTP request rate (`django_http_requests_total`)
- HTTP error rate (5xx ratio)
- HTTP latency p50/p95 (`django_http_requests_latency_seconds_bucket`)
- Celery task success/failure (`celery_task_total`)
- Celery task duration p95 (`celery_task_duration_seconds_bucket`)

## 6) Production guidance (minimal)

- Restrict `/metrics` in Nginx or via `METRICS_*` settings.
- Export traces to OTLP collector with `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Load `ops/alert_rules.yml` via Prometheus `rule_files`.
