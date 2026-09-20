# Security policy

Do not open a public issue for a vulnerability. Report it privately through the repository
owner's GitHub security advisory channel. Include affected version, reproduction, impact and
suggested mitigation without real credentials or personal data.

The sample API key, local Compose services and placeholder Kubernetes Secret are development
defaults only. Before production, follow `docs/production-guide.md`, use workload identity and
a secret manager, configure TLS and explicit egress, perform threat modeling, dependency/image
scanning, tenant-isolation tests and privacy review.

