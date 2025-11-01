---
layout: default
title: Operations
nav_order: 3
---

# Operations Guide

Practical guidance for running the Cloud Artifact Extractor in day-to-day operations: health checks, running in production, monitoring, scheduling, and maintenance.

## Health and Status

- Health endpoint: `GET /health`
- Recent jobs: `GET /extraction/jobs?limit=20`
- Job detail: `GET /extraction/jobs/{job_id}`

## Running in Production

- Use a process manager (systemd, supervisord, Docker, or Kubernetes)
- Configure `LOG_LEVEL=INFO` or `WARNING`
- Prefer HTTP transport to deliver artifacts to a central scanner

### Example: Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Scheduling Scans

Use the API to create schedules or an external scheduler (cron, Airflow, etc.).

### API-based schedule

```bash
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-full-scan",
    "cron_expression": "0 2 * * *",
    "batch_size": 200
  }'
```

## Monitoring and Logs

- Log to stdout by default; ship with your log agent
- Optionally enable metrics if supported by your deployment

## Backup and Retention (Filesystem Transport)

- Rotate the `file_collector` directory with logrotate or a cron job
- Archive to object storage for long-term retention

## Common Operational Tasks

- Update configuration with minimal restarts: environment overrides are read on startup
- Validate credentials regularly using provider CLIs

## Troubleshooting

See the dedicated [Troubleshooting]({{ '/troubleshooting.html' | relative_url }}) page for common errors and fixes.
