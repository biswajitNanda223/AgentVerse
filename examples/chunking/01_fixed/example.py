from agentverse.rag.chunking import FixedWindowChunker
from agentverse.rag.example_data import DOCUMENT

print(FixedWindowChunker(12, 2).split(DOCUMENT))
