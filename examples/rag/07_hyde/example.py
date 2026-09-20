from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import DenseRetriever, HyDERetriever

print(
    HyDERetriever(
        DenseRetriever(chunks()), lambda query: "CRAG evaluates retrieved evidence"
    ).search("What is CRAG?", "demo")
)
