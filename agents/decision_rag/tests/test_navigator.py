from collections.abc import Callable, Sequence

import pytest

from decision_rag.local import LexicalDecisionModel
from decision_rag.models import Candidate, DecisionModelError
from decision_rag.navigator import DecisionNavigator, NavigationConfig
from decision_rag.sample_corpus import sample_tree
from decision_rag.testing import ScriptedChoiceModel, ScriptedModel

DOC = "messaging/azure-event-hubs"
TARGET = f"{DOC}/kafka-compatibility/1"


def likes(*prefixes: str, high: float = 0.9, low: float = 0.05) -> ScriptedModel:
    """High score for any candidate whose id is an ancestor of, or is under, one of the prefixes."""

    def score(c: Candidate) -> float:
        hit = any(p.startswith(c.id) or c.id.startswith(p) for p in prefixes)
        return high if hit else low

    return ScriptedModel(score)


async def test_screens_documents_then_scores_only_the_passages_of_kept_documents() -> None:
    model = likes(DOC)
    config = NavigationConfig(keep_topics=1, keep_documents=1)
    result = await DecisionNavigator(sample_tree(), model, config).navigate("q")
    assert result.passages[0].node.id.startswith(DOC)
    judged = {i for call in model.calls for i in call}
    assert any(i.startswith("messaging/kafka-consumer-groups/") for i in judged) is False
    assert any(i.startswith("retrieval/") for i in judged) is False  # pruned topics never expanded
    passage_call = model.calls[-1]
    assert passage_call and all(i.startswith(f"{DOC}/") and i.count("/") == 3 for i in passage_call)
    assert [s.stage for s in result.steps] == ["topic", "document", "passage"]


async def test_every_candidate_of_a_stage_is_judged_in_the_same_call() -> None:
    model = likes(DOC)
    await DecisionNavigator(sample_tree(), model).navigate("q")
    assert sorted(model.calls[0]) == ["agents", "messaging", "retrieval"]  # all topics, one context


async def test_keeps_top_k_documents_and_top_r_passages() -> None:
    model = ScriptedModel(lambda c: (hash(c.id) % 97) / 100 + 0.01)
    config = NavigationConfig(keep_topics=3, keep_documents=2, keep_passages=2)
    result = await DecisionNavigator(sample_tree(), model, config).navigate("q")
    document_step = next(s for s in result.steps if s.stage == "document")
    assert sum(c.kept for c in document_step.candidates) == 2
    assert len(result.passages) == 2
    scores = [p.score for p in result.passages]
    assert scores == sorted(scores, reverse=True)


async def test_sections_are_skipped_by_default_and_judged_when_enabled() -> None:
    default = await DecisionNavigator(sample_tree(), likes(DOC)).navigate("q")
    assert "section" not in [s.stage for s in default.steps]
    with_sections = await DecisionNavigator(
        sample_tree(), likes(DOC), NavigationConfig(skip_sections=False)
    ).navigate("q")
    assert [s.stage for s in with_sections.steps] == ["topic", "document", "section", "passage"]


async def test_passages_are_ranked_by_their_own_yes_no_probability() -> None:
    def score(c: Candidate) -> float:
        if c.id == TARGET:
            return 0.9
        return 0.6 if c.level == 4 else 0.8  # ancestors score high, other passages lower

    result = await DecisionNavigator(sample_tree(), ScriptedModel(score)).navigate("q")
    assert result.passages[0].node.id == TARGET
    assert result.passages[0].score == result.passages[0].last_probability == 0.9


async def test_default_is_pure_top_k_with_no_probability_floor() -> None:
    result = await DecisionNavigator(sample_tree(), ScriptedModel(lambda c: 0.0)).navigate("q")
    assert sum(c.kept for c in result.steps[0].candidates) == 2  # keep_topics, though all are 0
    assert result.abstained  # nothing looked relevant, so it abstains instead of answering


async def test_optional_floor_with_no_signal_still_widens_instead_of_guessing() -> None:
    config = NavigationConfig(keep_topics=3, min_probability=0.5)
    result = await DecisionNavigator(sample_tree(), ScriptedModel(lambda c: 0.1), config).navigate(
        "q"
    )
    assert sum(c.kept for c in result.steps[0].candidates) == 3


async def test_abstains_when_the_best_passage_is_improbable() -> None:
    model = ScriptedModel(lambda c: 0.25 if c.level == 4 else 0.9)
    result = await DecisionNavigator(
        sample_tree(), model, NavigationConfig(abstain_below=0.3)
    ).navigate("q")
    assert result.abstained and result.passages


async def test_oversized_candidate_sets_run_as_a_tournament_then_a_joint_final() -> None:
    wanted = "messaging/dead-letter-queues"
    model = ScriptedModel(lambda c: 0.9 if c.id.startswith(wanted) else 0.05)
    config = NavigationConfig(max_candidates_per_call=4, keep_documents=2, keep_topics=3)
    result = await DecisionNavigator(sample_tree(), model, config).navigate("q")
    assert result.passages[0].node.id.startswith(wanted)
    assert all(len(call) <= 4 for call in model.calls)  # never exceeds the context budget
    assert any(s.model_calls > 1 for s in result.steps)
    assert any(c.probability is None for s in result.steps for c in s.candidates)


# ---- optional choice reranking -------------------------------------------------------------


def choice_model(distribution: Callable[[Sequence[Candidate]], list[float]]) -> ScriptedChoiceModel:
    return ScriptedChoiceModel(
        lambda c: 0.9 if c.id.startswith(DOC) or DOC.startswith(c.id) else 0.05, distribution
    )


async def test_rerank_asks_one_multiple_choice_question_over_the_top_r_and_reorders() -> None:
    model = choice_model(
        lambda cs: [0.1, 0.7, 0.2][: len(cs)] if len(cs) == 3 else [1 / len(cs)] * len(cs)
    )
    config = NavigationConfig(keep_topics=1, keep_documents=1, keep_passages=3, rerank=True)
    result = await DecisionNavigator(sample_tree(), model, config).navigate("q")
    assert len(model.choose_calls) == 1 and len(model.choose_calls[0]) == 3
    assert result.steps[-1].stage == "rerank" and result.steps[-1].model_calls == 1
    scores = [p.choice_probability for p in result.passages]
    assert scores == sorted(scores, reverse=True)  # type: ignore[type-var]
    assert result.passages[0].choice_probability == pytest.approx(0.7)
    assert result.passages[0].score == pytest.approx(0.7)
    assert result.model_calls == sum(s.model_calls for s in result.steps)


async def test_no_rerank_means_no_choice_call() -> None:
    model = choice_model(lambda cs: [1 / len(cs)] * len(cs))
    await DecisionNavigator(sample_tree(), model, NavigationConfig(rerank=False)).navigate("q")
    assert model.choose_calls == []


@pytest.mark.parametrize(
    "bad",
    [
        lambda cs: [0.5] * len(cs),  # does not sum to 1
        lambda cs: [1.0],  # wrong length
        lambda cs: [1.5, -0.5] + [0.0] * (len(cs) - 2),  # outside 0..1
    ],
)
async def test_invalid_choice_distributions_are_rejected(
    bad: Callable[[Sequence[Candidate]], list[float]],
) -> None:
    config = NavigationConfig(keep_topics=1, keep_documents=1, keep_passages=3, rerank=True)
    with pytest.raises(DecisionModelError):
        await DecisionNavigator(sample_tree(), choice_model(bad), config).navigate("q")


def test_rerank_requires_a_model_that_can_choose() -> None:
    with pytest.raises(ValueError, match="choose"):
        DecisionNavigator(
            sample_tree(), ScriptedModel(lambda c: 0.5), NavigationConfig(rerank=True)
        )


async def test_offline_stand_in_choose_is_a_distribution_and_rerank_runs() -> None:
    model = LexicalDecisionModel()
    candidates = [
        Candidate(f"c{i}", "t", text, 4)
        for i, text in enumerate(["dead letter topic", "kafka offsets", "graph"])
    ]
    distribution = await model.choose("dead letter", candidates)
    assert sum(distribution) == pytest.approx(1.0) and distribution[0] == max(distribution)
    config = NavigationConfig(rerank=True)
    result = await DecisionNavigator(sample_tree(), model, config).navigate(
        "What should I do with a poison message that retries cannot fix?"
    )
    assert result.passages[0].node.id == "messaging/dead-letter-queues/when-to-dead-letter/1"
    assert result.steps[-1].stage == "rerank"


# ---- validation ----------------------------------------------------------------------------


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
    for bad in (
        {"keep_documents": 0},
        {"keep_passages": 0},
        {"max_candidates_per_call": 1},
        {"min_probability": 1.5},
        {"rerank": True, "keep_passages": 50, "max_candidates_per_call": 10},
    ):
        with pytest.raises(ValueError):
            NavigationConfig(**bad)  # type: ignore[arg-type]
    assert NavigationConfig().keep_for("document") == 3
    assert NavigationConfig().skipped_kinds == frozenset({"section"})


async def test_offline_stand_in_navigates_to_the_right_branch() -> None:
    result = await DecisionNavigator(sample_tree(), LexicalDecisionModel()).navigate(
        "What should I do with a poison message that retries cannot fix?"
    )
    assert result.passages[0].node.id == "messaging/dead-letter-queues/when-to-dead-letter/1"
