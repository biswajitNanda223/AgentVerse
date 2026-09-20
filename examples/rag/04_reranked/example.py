from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import DenseRetriever, RerankingRetriever

retriever = RerankingRetriever(
    DenseRetriever(chunks()), lambda query, chunk: float(query.lower() in chunk.text.lower())
)
print(retriever.search("Hybrid RAG", "demo"))
