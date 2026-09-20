from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import DenseRetriever, MultiQueryRetriever, simple_query_expander

print(
    MultiQueryRetriever(DenseRetriever(chunks()), simple_query_expander).search(
        "How does CRAG work?", "demo"
    )
)
