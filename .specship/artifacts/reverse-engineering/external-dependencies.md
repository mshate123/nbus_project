# External Dependencies and Configuration

## Runtime services
- PostgreSQL 15: `DATABASE_URL`; Compose exposes 5432.
- LocalStack S3: `AWS_ENDPOINT_URL`, region, access key/secret, `S3_BUCKET_STATEMENTS`; no application consumer found.
- Docker Compose and nginx for local app.
- Minikube/kubectl for local Kubernetes manifests.

## Secrets/config risks
- Compose and Kubernetes manifests contain development credentials (`ledger`, `dev-token`, `test`) directly in configuration.
- `.env.example` documents `AUTH_STUB_TOKEN`, but API does not consume it.
- Kubernetes `frontend-deployment.yaml` sets `VITE_API_BASE_URL`, but `frontend/src/lib/api.ts` hardcodes `/api`; the env var is dead.
- Kubernetes frontend container port/probe target 3000 conflicts with nginx's configured listen port 80.
- API deployment omits `AUTH_STUB_TOKEN` and several documented settings.

## Rebuild stance
Use typed settings with environment validation, separate dev/test/prod values, no checked-in secrets, explicit readiness semantics, and one deployment target before adding Minikube complexity.
