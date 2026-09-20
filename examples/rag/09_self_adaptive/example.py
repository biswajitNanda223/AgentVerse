from agentverse.rag.example_data import chunks
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from agentverse.rag.strategies import AdaptiveRag, RetrievalDecision, SelfRag

base = InMemoryLexicalRetriever(chunks())
self_rag = SelfRag(
    base, lambda query: RetrievalDecision(True, "knowledge question"), lambda query, hits: hits
)
adaptive = AdaptiveRag(
    base, CorrectiveRag(base), lambda query: "complex" if "compare" in query else "simple"
)
print(self_rag.retrieve("CRAG", "demo"))
print(adaptive.retrieve("compare RAG approaches", "demo"))
