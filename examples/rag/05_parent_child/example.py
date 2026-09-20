from agentverse.rag.advanced_chunking import ParentChildChunker
from agentverse.rag.example_data import DOCUMENT
from agentverse.rag.strategies import DenseRetriever, ParentDocumentRetriever

parents, children = ParentChildChunker(parent_words=20, child_words=8, child_overlap=1).split(
    DOCUMENT
)
print(
    ParentDocumentRetriever(DenseRetriever(children), {item.id: item for item in parents}).search(
        "evidence", "demo"
    )
)
