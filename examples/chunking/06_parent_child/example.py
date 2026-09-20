from agentverse.rag.advanced_chunking import ParentChildChunker
from agentverse.rag.example_data import DOCUMENT

print(ParentChildChunker(20, 8, 1).split(DOCUMENT))
