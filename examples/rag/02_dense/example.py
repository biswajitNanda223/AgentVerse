from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import DenseRetriever

print(DenseRetriever(chunks()).search("semantic vector search", "demo", 2))
