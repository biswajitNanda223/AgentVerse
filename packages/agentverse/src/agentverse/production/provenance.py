from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class Lineage:
    request_id: str
    tenant_id: str
    agent_version: str
    prompt_version: str
    model: str
    index_version: str
    source_uri: str
    content_sha256: str
    created_at: datetime


def create_lineage(
    *,
    request_id: str,
    tenant_id: str,
    agent_version: str,
    prompt_version: str,
    model: str,
    index_version: str,
    source_uri: str,
    content: str,
) -> Lineage:
    """Bind an output to the exact agent, prompt, model, index and evidence version."""

    return Lineage(
        request_id=request_id,
        tenant_id=tenant_id,
        agent_version=agent_version,
        prompt_version=prompt_version,
        model=model,
        index_version=index_version,
        source_uri=source_uri,
        content_sha256=sha256(content.encode()).hexdigest(),
        created_at=datetime.now(UTC),
    )


def verify_lineage(lineage: Lineage, *, tenant_id: str, content: str) -> bool:
    """Fail closed if evidence crosses a tenant or its content no longer matches."""

    digest = sha256(content.encode()).hexdigest()
    return lineage.tenant_id == tenant_id and lineage.content_sha256 == digest
