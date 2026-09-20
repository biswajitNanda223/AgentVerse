import sqlite3
from datetime import UTC, datetime

from agentverse.rag.example_data import chunks
from agentverse.rag.strategies import DenseRetriever, SqlRag, TemporalRetriever

database = sqlite3.connect(":memory:")
database.execute("CREATE TABLE facts(name TEXT, value TEXT)")
database.execute("INSERT INTO facts VALUES ('rag', 'retrieval augmented generation')")
print(
    SqlRag(database, {"fact": "SELECT value FROM facts WHERE name=:name"}).execute(
        "fact", {"name": "rag"}
    )
)
database.close()
print(
    TemporalRetriever(DenseRetriever(chunks()), now=lambda: datetime.now(UTC)).search("RAG", "demo")
)
