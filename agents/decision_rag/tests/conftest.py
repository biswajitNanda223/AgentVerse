from collections.abc import Callable

import pytest

from decision_rag.testing import ScriptedModel


@pytest.fixture
def prefer() -> Callable[[str], ScriptedModel]:
    """prefer('messaging/azure') -> 0.9 for ids under that prefix, 0.05 otherwise."""

    def make(prefix: str) -> ScriptedModel:
        return ScriptedModel(lambda c: 0.9 if c.id.startswith(prefix) else 0.05)

    return make
