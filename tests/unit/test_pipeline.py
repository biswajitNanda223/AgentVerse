from agentverse.rag.models import Chunk
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever


def test_corrective_rag_uses_original_query_for_grading() -> None:
    chunk = Chunk("c", "d", "hybrid retrieval", 0, "memory://c", "t", 0, 16)
    seen: list[str] = []

    def grader(query: str, _candidate: object) -> float:
        seen.append(query)
        return 1.0

    rag = CorrectiveRag(InMemoryLexicalRetriever([chunk]), grader=grader)
    answer = rag.retrieve("hybrid", "t")
    assert answer.citations == ("memory://c",)
    assert seen == ["hybrid"]
