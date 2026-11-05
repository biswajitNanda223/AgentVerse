class SystemOneError(Exception):
    """The System One call failed. Callers must route to a safe fallback, not guess."""


class WireFormatError(SystemOneError):
    """The service answered, but not in a shape that matches the questions asked."""
