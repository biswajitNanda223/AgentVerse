from collections.abc import Callable, Sequence

import pytest

from decision_rag.local import LexicalDecisionModel
from decision_rag.models import Candidate, DecisionModelError
from decision_rag.navigator import DecisionNavigator, NavigationConfig
from decision_rag.sample_corpus import sample_tree
from decision_rag.testing import ScriptedModel


async def test_descends_one_joint_call_per_level_to_the_best_passage(
    prefer: Callable[[str], ScriptedModel],
) -> None:
    del prefer  # this test needs ancestor-aware scores, so it builds its own model
    model = ScriptedModel(
        lambda c: (
            0.9 if "messaging/azure-event-hubs/kafka-compatibility/1".startswith(c.id) else 0.05
        )
    )
    result = await DecisionNavigator(sample_tree(), model).navigate("anything")
    assert result.passages[0].node.id == "messaging/azure-event-hubs/kafka-compatibility/1"
    assert result.model_calls == 4  # topic, document, section, passage levels
    assert len(model.calls) == 4
    assert not result.abstained


async def test_every_candidate_at_a_level_is_judged_in_the_same_call(
    prefer: Callable[[str], ScriptedModel],
) -> None:
    model = prefer("messaging")
    await DecisionNavigator(sample_tree(), model).navigate("q")
    first = model.calls[0]
    assert sorted(first) == ["agents", "messaging", "retrieval"]  # all topics, one context


async def test_beam_width_limits_branches_and_trace_marks_pruned_ones() -> None:
    model = ScriptedModel(lambda c: 0.8)  # everything looks relevant
    result = await DecisionNavigator(sample_tree(), model, NavigationConfig(beam_width=1)).navigate(
        "q"
    )
    for step in result.steps:
        assert sum(c.kept for c in step.candidates) == 1
    assert result.passages  # a single beam still reaches a passage


async def test_no_signal_widens_the_beam_instead_of_guessing_one_branch() -> None:
    model = ScriptedModel(lambda c: 0.0)  # nothing looks relevant anywhere
    result = await DecisionNavigator(sample_tree(), model, NavigationConfig(beam_width=3)).navigate(
        "q"
    )
    assert sum(c.kept for c in result.steps[0].candidates) == 3
    assert result.abstained


async def test_abstains_when_the_best_passage_is_improbable() -> None:
    model = ScriptedModel(lambda c: 0.25 if c.level == 4 else 0.9)
    result = await DecisionNavigator(
        sample_tree(), model, NavigationConfig(abstain_below=0.3)
    ).navigate("q")
    assert result.abstained and result.passages


async def test_oversized_candidate_sets_run_as_a_tournament_then_a_joint_final() -> None:
    wanted = "messaging/dead-letter-queues"
    model = ScriptedModel(lambda c: 0.9 if c.id.startswith(wanted) else 0.05)
    config = NavigationConfig(max_candidates_per_call=4, beam_width=2)
    result = await DecisionNavigator(sample_tree(), model, config).navigate("q")
    assert result.passages[0].node.id.startswith(wanted)
    assert all(len(call) <= 4 for call in model.calls)  # never exceeds the context budget
    document_step = result.steps[1]  # 9 documents > 4: needs chunking
    assert document_step.model_calls > 1
    assert any(c.probability is None for c in document_step.candidates)  # dropped early


@pytest.mark.parametrize(
    "bad",
    [lambda c: 1.5, lambda c: -0.1, lambda c: float("nan")],
)
async def test_out_of_range_probabilities_are_rejected(bad: Callable[[Candidate], float]) -> None:
    with pytest.raises(DecisionModelError, match=r"outside 0\.\.1"):
        await DecisionNavigator(sample_tree(), ScriptedModel(bad)).navigate("q")


async def test_wrong_number_of_judgments_is_rejected() -> None:
    class Short:
        async def judge(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
            return [0.5]

    with pytest.raises(DecisionModelError, match="wrong number"):
        await DecisionNavigator(sample_tree(), Short()).navigate("q")


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        NavigationConfig(beam_width=0)
    with pytest.raises(ValueError):
        NavigationConfig(max_candidates_per_call=1)
    with pytest.raises(ValueError):
        NavigationConfig(min_probability=1.5)


async def test_offline_stand_in_navigates_to_the_right_branch() -> None:
    result = await DecisionNavigator(sample_tree(), LexicalDecisionModel()).navigate(
        "What should I do with a poison message that retries cannot fix?"
    )
    assert result.passages[0].node.id == "messaging/dead-letter-queues/when-to-dead-letter/1"
