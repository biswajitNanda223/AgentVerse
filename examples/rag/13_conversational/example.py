from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import ConversationalRetriever, DenseRetriever

retriever = ConversationalRetriever(
    DenseRetriever(chunks()), lambda history, query: " ".join([*history, query])
)
print(retriever.search("How does it grade?", "demo", history=["We discussed CRAG."]))
