from agentverse.rag.advanced_chunking import SemanticChunker
from agentverse.rag.example_data import DOCUMENT

print(SemanticChunker(breakpoint=0.1).split(DOCUMENT))
