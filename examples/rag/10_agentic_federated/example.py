from agentverse.rag.example_data import chunks
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from agentverse.rag.strategies import AgenticRag, FederatedRetriever

sources = {
    "docs": InMemoryLexicalRetriever(chunks()),
    "runbooks": InMemoryLexicalRetriever(chunks()),
}
federated = FederatedRetriever(sources)
agentic = AgenticRag(sources, lambda query, names: [(query, name) for name in names])
print(federated.search("multi-hop", "demo"))
print(agentic.retrieve("multi-hop", "demo"))
