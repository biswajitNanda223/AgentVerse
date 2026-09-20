from agentverse.rag.advanced_chunking import ParagraphChunker, SentenceChunker
from agentverse.rag.example_data import DOCUMENT

print(SentenceChunker(15).split(DOCUMENT))
print(ParagraphChunker(30).split(DOCUMENT))
