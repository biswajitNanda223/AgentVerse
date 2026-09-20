# Deployment runbook

## Local

```bash
cp .env.example .env
uv sync --extra dev --extra rag --extra ocr
docker compose -f deploy/docker-compose.yml up --build
curl http://localhost:8000/health/live
```

## Container and Kubernetes

Build an immutable image, scan it, push by digest, apply the namespace/config/secrets through
your GitOps system, run migrations/index compatibility checks as a separate job, deploy a
canary, run smoke/eval gates, then promote. The example manifests include non-root execution,
read-only filesystem, resource requests/limits, probes, HPA, PDB and deny-by-default egress.

```bash
docker build -f deploy/Dockerfile -t agentverse:0.1.0 .
kubectl apply -f deploy/k8s/
kubectl rollout status deployment/agentverse-api -n agentverse
```

Replace example ConfigMaps and Secrets with External Secrets/Secret Manager. Set an explicit
model-provider egress destination, managed Postgres/Redis/vector store, TLS ingress, workload
identity and an OTLP collector. Do not use Compose credentials in production.

## Google deployment options

- Cloud Run: simplest stateless API/agent service; pair with managed state and async workers.
- GKE: use when network isolation, sidecars, custom autoscaling or specialized compute matters.
- Agent Runtime: managed ADK execution and lifecycle integration.

For a generated Google deployment scaffold, run
`agents-cli scaffold enhance --deployment-target cloud_run` (or the required target), review
Terraform and IAM, then deploy through CI. Cloud Trace is available in the Agents CLI workflow;
provision content analytics only after privacy approval.

## Release gates and rollback

1. Unit/contract/security tests and dependency/image scans.
2. Retrieval golden-set regression and agent trajectory/safety evals.
3. Load test at expected concurrency plus provider quota failure test.
4. Canary by tenant/traffic percentage; compare quality, cost and latency.
5. Roll back image, prompt, model and index versions independently. Keep compatibility metadata
   so an application rollback never queries an incompatible index.

