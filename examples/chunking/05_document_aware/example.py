from agentverse.rag.advanced_chunking import MarkdownChunker
from agentverse.rag.models import Document

document = Document(
    "md", "# RAG\nEvidence first.\n## Evaluation\nMeasure recall.", "memory://md", "demo"
)
print(MarkdownChunker().split(document))
