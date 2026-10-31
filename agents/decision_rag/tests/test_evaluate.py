from decision_rag.evaluate import evaluate
from decision_rag.settings import DecisionRagSettings


async def test_eval_harness_runs_and_uses_one_call_per_level() -> None:
    report = await evaluate(DecisionRagSettings())
    assert report.queries == 10
    assert report.mean_model_calls == 4.0
    # Machinery regression guard for the word-matching stand-in. Not evidence about accuracy.
    assert report.navigator_hit1 >= 0.7
