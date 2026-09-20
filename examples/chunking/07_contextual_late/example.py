from agentverse.rag.advanced_chunking import LateChunker
from agentverse.rag.chunking import FixedWindowChunker, contextualize
from agentverse.rag.example_data import DOCUMENT

print(contextualize(FixedWindowChunker(12, 2).split(DOCUMENT), "AgentVerse RAG guide"))
print(LateChunker().split(DOCUMENT))
