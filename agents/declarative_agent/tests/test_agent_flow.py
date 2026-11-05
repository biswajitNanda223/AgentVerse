from google.adk.models.llm_request import LlmRequest

from declarative_agent.adk_agent import root_agent
from declarative_agent.testing import (
    ScriptedLlm,
    call,
    final_text,
    responses,
    run_turns,
    say,
)

GOOD_SQL = (
    "SELECT id, activity_name, variance_days FROM p6_activity_dc "
    "WHERE project = 'Chennai DC-1' LIMIT 5"
)


def agent_with(script):  # type: ignore[no-untyped-def]
    agent = root_agent.clone()
    llm = ScriptedLlm(script=script)
    agent.model = llm
    return agent, llm


async def test_skill_loading_unlocks_the_sql_tool_and_the_guardrail_blocks_bad_queries() -> None:
    plan = [
        call("list_skills"),
        call("load_skill", skill_name="governed-sql"),
        call("run_governed_sql", sql=GOOD_SQL),
        call("run_governed_sql", sql="DROP TABLE p6_activity_dc"),
        call("run_governed_sql", sql="SELECT po_number FROM other_bu_pos LIMIT 5"),
        say("Foundation piling is 8 days late [p6_activity_dc:1]."),
    ]
    agent, llm = agent_with(lambda i, r: plan[i])
    events = await run_turns(agent, "How late is piling at Chennai DC-1?")

    assert "run_governed_sql" not in llm.seen_tools[0]  # not visible before the skill is loaded
    assert "load_skill" in llm.seen_tools[0] and "list_skills" in llm.seen_tools[0]
    assert "run_governed_sql" in llm.seen_tools[3]  # visible after load_skill

    ok, dropped, foreign = responses(events, "run_governed_sql")
    assert ok["rows"][0]["variance_days"] == 8 and ok["citations"] == [
        "p6_activity_dc:1",
        "p6_activity_dc:2",
    ]
    assert "citation_hint" not in ok
    assert dropped["blocked"] and "read-only" in dropped["reason"]
    assert foreign["blocked"] and "not available" in foreign["reason"]
    assert "8 days" in final_text(events)


async def test_session_state_limits_tables_and_hides_masked_columns() -> None:
    plan = [
        call("load_skill", skill_name="governed-sql"),
        call("run_governed_sql", sql="SELECT po_number, unit_price FROM ariba_po_status LIMIT 5"),
        call(
            "run_governed_sql", sql="SELECT po_number, delivery_date FROM ariba_po_status LIMIT 5"
        ),
        call("run_governed_sql", sql="SELECT activity_name FROM p6_activity_dc LIMIT 5"),
        say("done"),
    ]
    agent, _ = agent_with(lambda i, r: plan[i])
    state = {"allowed_tables": ["ariba_po_status"], "masked_columns": ["unit_price"]}
    events = await run_turns(agent, "show POs", state)
    masked, allowed, other_table = responses(events, "run_governed_sql")
    assert masked["blocked"] and "unit_price" in masked["reason"]
    assert "blocked" not in allowed and allowed["row_count"] == 2
    assert other_table["blocked"] and "p6_activity_dc" in other_table["reason"]


async def test_write_back_only_drafts_and_is_idempotent() -> None:
    args = {
        "system": "SAP",
        "record_id": "4500192",
        "field": "delivery_date",
        "new_value": "2026-04-05",
    }
    plan = [
        call("load_skill", skill_name="write-back-approval"),
        call("stage_write_back", **args),
        call("stage_write_back", **args),
        call("stage_write_back", system="Oracle", record_id="1", field="f", new_value="v"),
        say("Draft staged, awaiting approval."),
    ]
    agent, llm = agent_with(lambda i, r: plan[i])
    events = await run_turns(agent, "move the delivery date")
    assert "stage_write_back" not in llm.seen_tools[0] and "stage_write_back" in llm.seen_tools[1]
    first, second, invalid = responses(events, "stage_write_back")
    assert first["status"] == "awaiting_approval" and first["executed"] is False
    assert second["draft_id"] == first["draft_id"] and second["duplicate"] is True
    assert "error" in invalid and invalid["executed"] is False


async def test_the_model_call_budget_stops_a_runaway_loop_with_a_partial_answer() -> None:
    def looping(i: int, request: LlmRequest):  # type: ignore[no-untyped-def]
        return call("list_skills")  # a model that never converges

    agent, llm = agent_with(looping)
    events = await run_turns(agent, "ambiguous question", {"max_llm_calls": 3})
    assert llm.calls == 3  # the fourth request was stopped before reaching the model
    text = final_text(events)
    assert "Stopped after 3 model calls (limit 3)" in text
    assert "Partial answer" in text


async def test_the_budget_summary_contains_only_gathered_evidence() -> None:
    plan = [
        call("load_skill", skill_name="governed-sql"),
        call("run_governed_sql", sql=GOOD_SQL),
        call("list_skills"),
        call("list_skills"),
    ]
    agent, _ = agent_with(lambda i, r: plan[min(i, len(plan) - 1)])
    events = await run_turns(agent, "q", {"max_llm_calls": 4})
    text = final_text(events)
    assert "run_governed_sql" in text and "variance_days" in text
    assert "invented" not in text


async def test_the_default_budget_is_the_requirement_value() -> None:
    from declarative_agent.callbacks import DEFAULT_MAX_LLM_CALLS

    assert DEFAULT_MAX_LLM_CALLS == 45


async def test_rows_without_a_key_column_come_back_with_a_citation_hint() -> None:
    plan = [
        call("load_skill", skill_name="governed-sql"),
        call("run_governed_sql", sql="SELECT activity_name FROM p6_activity_dc LIMIT 2"),
        say("done"),
    ]
    agent, _ = agent_with(lambda i, r: plan[i])
    [result] = responses(await run_turns(agent, "q"), "run_governed_sql")
    assert result["citations"] == [] and "citation_hint" in result
