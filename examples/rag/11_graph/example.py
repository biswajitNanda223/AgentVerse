from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import GraphEdge, GraphRetriever

items = chunks()
graph = GraphRetriever(
    {item.id: item for item in items}, [GraphEdge("CRAG", "grades", "evidence", "c2")]
)
print(graph.search("Which system grades evidence?", "demo"))
