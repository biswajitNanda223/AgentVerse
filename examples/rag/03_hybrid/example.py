from agentverse.rag.example_data import chunks
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from agentverse.rag.strategies import DenseRetriever, HybridRetriever

items = chunks()
print(
    HybridRetriever(DenseRetriever(items), InMemoryLexicalRetriever(items)).search(
        "hybrid keywords", "demo"
    )
)
