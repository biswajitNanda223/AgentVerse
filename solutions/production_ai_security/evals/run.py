from __future__ import annotations

import json
from pathlib import Path

from solutions.production_ai_security.app.evaluation import retrieval_recall
from solutions.production_ai_security.app.models import Evidence
from solutions.production_ai_security.app.retrieval import SecureRetriever


def main() -> None:
    retriever = SecureRetriever(
        (
            Evidence(
                "consent",
                "Sensitive actions require explicit human approval and consent.",
                "docs://security/consent",
                "public",
                1.0,
                True,
            ),
        )
    )
    cases = (
        Path(__file__).with_name("security_golden.jsonl").read_text(encoding="utf-8").splitlines()
    )
    failures: list[str] = []
    for line in cases:
        case = json.loads(line)
        result = retrieval_recall(
            retriever.search(case["query"], tenant_id=case["tenant_id"]),
            set(case["expected_ids"]),
        )
        if result.score < case["minimum_recall"]:
            failures.append(f"{case['name']}: {result.reason}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"security evaluation gate passed: {len(cases)} cases")


if __name__ == "__main__":
    main()
