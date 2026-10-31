"""`python -m decision_rag "question" [--trace] [--mermaid FILE] [--corpus DIR]`."""

import argparse
import asyncio
import json
from pathlib import Path

from decision_rag.factory import build_pipeline
from decision_rag.mermaid import trace_to_mermaid
from decision_rag.settings import DecisionRagSettings, get_settings


def _print_trace(answer_nav: object) -> None:
    from decision_rag.navigator import NavigationResult

    assert isinstance(answer_nav, NavigationResult)
    for step in answer_nav.steps:
        print(f"\nstep {step.step}: {len(step.candidates)} candidates, {step.model_calls} call(s)")
        for cand in sorted(step.candidates, key=lambda c: -(c.probability or 0)):
            p = "  -  " if cand.probability is None else f"{cand.probability:.2f}"
            print(f"  {'KEEP' if cand.kept else '    '} {p}  [{cand.kind}] {cand.title}")
    print(
        f"\n{answer_nav.model_calls} decision-model call(s) in {answer_nav.seconds * 1000:.0f} ms"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(prog="decision_rag")
    parser.add_argument("query")
    parser.add_argument("--corpus", help="folder of Markdown files (default: built-in sample)")
    parser.add_argument("--trace", action="store_true", help="print every candidate judged")
    parser.add_argument(
        "--mermaid", metavar="FILE", help="write the navigation as a Mermaid diagram"
    )
    args = parser.parse_args()

    base = get_settings()
    settings = (
        DecisionRagSettings(
            **{**base.model_dump(), "api_key": base.api_key, "corpus_dir": args.corpus}
        )
        if args.corpus
        else base
    )
    answer = await build_pipeline(settings).answer(args.query)
    print(
        json.dumps(
            {
                "abstained": answer.abstained,
                "reason": answer.reason,
                "answer": answer.text,
                "citations": [
                    {"path": c.path, "probability": c.probability} for c in answer.citations
                ],
            },
            indent=2,
        )
    )
    if answer.navigation and args.trace:
        _print_trace(answer.navigation)
    if answer.navigation and args.mermaid:
        Path(args.mermaid).write_text(trace_to_mermaid(answer.navigation), encoding="utf-8")
        print(f"\nwrote {args.mermaid}")


if __name__ == "__main__":
    asyncio.run(main())
