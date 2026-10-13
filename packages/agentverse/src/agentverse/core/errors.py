class AgentVerseError(Exception):
    """Base application error safe to map at a process boundary."""


class InvalidDocumentError(AgentVerseError):
    """The submitted document violates an ingestion contract."""


class RetrievalError(AgentVerseError):
    """Retrieval could not produce a trustworthy result."""
