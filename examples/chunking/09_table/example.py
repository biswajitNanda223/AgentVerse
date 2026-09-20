from agentverse.rag.advanced_chunking import TableChunker
from agentverse.rag.models import Document

csv_text = "name,type\nnaive,rag\nhybrid,rag\nsemantic,chunking\n"
print(TableChunker(2).split(Document("table", csv_text, "memory://table", "demo")))
