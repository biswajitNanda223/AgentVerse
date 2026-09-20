from agentverse.rag.chunking import RecursiveChunker
from agentverse.rag.example_data import DOCUMENT

print(RecursiveChunker(15, 2).split(DOCUMENT))
