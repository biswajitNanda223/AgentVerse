from agentverse.rag.example_data import chunks
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever

print(
    CorrectiveRag(
        InMemoryLexicalRetriever(chunks()), rewriter=lambda query: f"{query} evidence"
    ).retrieve("CRAG", "demo")
)
