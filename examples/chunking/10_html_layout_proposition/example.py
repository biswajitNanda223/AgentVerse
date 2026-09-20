from agentverse.rag.advanced_chunking import (
    HtmlChunker,
    LayoutAwareChunker,
    LayoutElement,
    PropositionChunker,
)
from agentverse.rag.models import Document

html = Document("html", "<h1>RAG</h1><p>Ground answers in evidence.</p>", "memory://html", "demo")
print(HtmlChunker().split(html))
print(
    LayoutAwareChunker().split_elements(
        html, [LayoutElement("RAG diagram", page=1, kind="figure", coordinates=(0, 0, 100, 100))]
    )
)
print(PropositionChunker(lambda text: ["RAG uses evidence."]).split(html))
