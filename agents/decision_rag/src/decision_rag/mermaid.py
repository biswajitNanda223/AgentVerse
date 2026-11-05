"""Render a real navigation trace as a Mermaid flowchart you can view on GitHub."""

from __future__ import annotations

import re

from decision_rag.corpus import ROOT_ID
from decision_rag.navigator import NavigationResult


def _safe(text: str, limit: int = 38) -> str:
    text = re.sub(r"[\"'`<>\[\]{}|()#;&\\]", "", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def trace_to_mermaid(result: NavigationResult) -> str:
    final = {p.node.id for p in result.passages}
    rank = {p.node.id: i for i, p in enumerate(result.passages, start=1)}
    ids: dict[str, str] = {ROOT_ID: "n0"}
    calls = f"{result.model_calls} joint judgments, {len(result.steps)} stages"
    lines = ["flowchart TD", f'  n0(["Query: {_safe(result.query, 60)}<br/>{calls}"])']
    classes = [
        "  classDef kept fill:#d7f0dd,stroke:#2e7d32,color:#000",
        "  classDef pruned fill:#eeeeee,stroke:#9e9e9e,color:#555",
        "  classDef answer fill:#fff3c4,stroke:#b8860b,stroke-width:3px,color:#000",
        "  classDef root fill:#dbe8ff,stroke:#2f5fb3,color:#000",
    ]
    members: dict[str, list[str]] = {"kept": [], "pruned": [], "answer": []}
    for step in result.steps:
        if step.stage == "rerank":
            continue  # shown as rank and choice probability on the passage nodes
        for cand in step.candidates:
            ids[cand.node_id] = f"n{len(ids)}"
            label = _safe(cand.title)
            p = "pruned early" if cand.probability is None else f"p={cand.probability:.2f}"
            if cand.node_id in rank:
                chosen = result.passages[rank[cand.node_id] - 1].choice_probability
                extra = "" if chosen is None else f", choice={chosen:.2f}"
                p = f"rank {rank[cand.node_id]} · {p}{extra}"
            lines.append(f'  {ids[cand.node_id]}["{label}<br/>{cand.kind} · {p}"]')
            bucket = "answer" if cand.node_id in final else "kept" if cand.kept else "pruned"
            members[bucket].append(ids[cand.node_id])
    for step in result.steps:
        if step.stage == "rerank":
            continue
        for cand in step.candidates:
            arrow = "-->" if cand.kept else "-.->"
            lines.append(f"  {ids[cand.parent_id]} {arrow} {ids[cand.node_id]}")
    lines += classes
    lines.append("  class n0 root")
    for bucket, nodes in members.items():
        if nodes:
            lines.append(f"  class {','.join(nodes)} {bucket}")
    return "\n".join(lines) + "\n"
