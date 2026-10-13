"""Fail when a tracked Markdown file has a broken relative link or an unterminated code fence."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
EXTERNAL = re.compile(r"^(?:https?:|mailto:)")


def main() -> int:
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    files = subprocess.run(
        ["git", "ls-files", "*.md"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    ).stdout.split()
    errors: list[str] = []
    for name in files:
        path = root / name
        text = path.read_text(encoding="utf-8")
        if text.count("```") % 2:
            errors.append(f"{name}: unterminated code fence")
        for match in LINK.finditer(text):
            target = match.group(1)
            if EXTERNAL.match(target):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"{name}: broken link -> {target}")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"checked {len(files)} markdown files, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
