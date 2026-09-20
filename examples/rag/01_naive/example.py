from agentverse.rag.example_data import chunks
from agentverse.rag.retrieval import InMemoryLexicalRetriever

print(InMemoryLexicalRetriever(chunks()).search("evidence grading", "demo", 2))
