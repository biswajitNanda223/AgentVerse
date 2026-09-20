from agentverse.rag.advanced_chunking import PythonCodeChunker
from agentverse.rag.models import Document

code = "import math\n\ndef area(radius: float) -> float:\n    return math.pi * radius**2\n"
print(PythonCodeChunker().split(Document("code", code, "memory://code", "demo")))
