from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import MultimodalItem, MultimodalRetriever

items = chunks()
index = [MultimodalItem(items[0], "image", "diagram showing vectors plus keyword search")]
print(MultimodalRetriever(index).search("vector keyword diagram", "demo"))
