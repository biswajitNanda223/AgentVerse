"""Build a sample PDF from Markdown files, so the PDF loader can be exercised on real layout.

`python -m decision_rag.sample_pdf <markdown folder or files...> <out.pdf>`.
`# Title` becomes a large title, `## Heading` a bold section heading, other lines paragraphs.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

CSS = """
h1 { font-size: 18pt; font-weight: bold; margin-top: 18pt; margin-bottom: 8pt; }
h2 { font-size: 11.5pt; font-weight: bold; margin-top: 10pt; margin-bottom: 3pt; }
p  { font-size: 10pt; margin-top: 0pt; margin-bottom: 4pt; }
"""


def markdown_to_html(markdown: str) -> str:
    parts: list[str] = []
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,2})\s+(.*)", line)
        if match:
            tag = "h1" if len(match.group(1)) == 1 else "h2"
            parts.append(f"<{tag}>{html.escape(match.group(2).strip())}</{tag}>")
        elif line.strip():
            parts.append(f"<p>{html.escape(line.strip())}</p>")
    return "\n".join(parts)


def _natural(path: Path) -> list[int | str]:
    """Sort domain-2.md before domain-10.md."""

    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.name)]


def build_pdf(markdown_files: list[Path], out: Path) -> int:
    """Write the PDF and return its page count."""

    import pymupdf

    body = "\n".join(markdown_to_html(p.read_text(encoding="utf-8")) for p in markdown_files)
    story = pymupdf.Story(html=body, user_css=CSS)
    page_box = pymupdf.paper_rect("a4")
    content = pymupdf.Rect(page_box.x0 + 50, page_box.y0 + 50, page_box.x1 - 50, page_box.y1 - 60)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = pymupdf.DocumentWriter(str(out))
    more = 1
    while more:
        device = writer.begin_page(page_box)
        more, _ = story.place(content)
        story.draw(device)
        writer.end_page()
    writer.close()
    with pymupdf.open(out) as pdf:
        return int(pdf.page_count)


if __name__ == "__main__":
    *inputs, target = sys.argv[1:]
    files: list[Path] = []
    for item in inputs:
        path = Path(item)
        files += (
            sorted(
                path.glob("*.md"),
                key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)],
            )
            if path.is_dir()
            else [path]
        )
    if not files:
        raise SystemExit("usage: python -m decision_rag.sample_pdf <md dir or files> <out.pdf>")
    print(f"wrote {target} ({build_pdf(files, Path(target))} pages)")
