# Event Catalog

No application event bus, WebSocket channel, or queue producer/consumer was found in the tracked source.

- Kubernetes CronJob is the only asynchronous trigger described: `infra/k8s/accrual-cronjob.yaml`.
- It references missing module `backend.jobs.accrual`.
- LocalStack is configured for S3 in `docker-compose.yml`, but no S3 client, export route, bucket bootstrap, or object lifecycle implementation was found.
- SQS/event bus is explicitly out of scope in `.kiro/specs/core-ledger/requirements.md`.

## Rebuild implication
Treat daily accrual as a command/job boundary with an explicit idempotent service API. Remove LocalStack/S3 from the first rebuild unless statement export is explicitly reintroduced; otherwise it is dead infrastructure rather than a working dependency.
