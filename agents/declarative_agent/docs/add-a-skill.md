# Add a skill

1. **Create the folder**, named exactly like the skill (lowercase words joined by hyphens):

   ```text
   src/declarative_agent/skills/my-skill/
     SKILL.md
     references/details.md      # optional, level 3
   ```

2. **Write `SKILL.md`**: frontmatter, then the procedure.

   ```markdown
   ---
   name: my-skill
   description: Use when <the situation>. <What it unlocks or teaches, in one sentence.>
   license: Apache-2.0
   metadata:
     adk_additional_tools:      # optional: tools that appear only after this skill is loaded
       - my_tool
   ---

   # My skill

   1. Step the model should follow.
   2. Another step. Point to `references/details.md` for rare detail.
   ```

   The folder name must equal `name`, or loading fails. Keep the description to the *when*: it
   is the only part always in context.

3. **If it unlocks a tool**, write the function in `tools.py` (with a docstring, since the model
   reads it) and add it to `additional_tools` in `skill_set.py`. If the tool is risky, also add a
   rule for it in `callbacks.tool_guardrail`; a skill gates visibility, not safety.

4. **Test it.** Add the name to `EXPECTED_SKILLS` in `tests/test_definition.py`, add the unlock to
   the expected map, and add a flow test in `tests/test_agent_flow.py` with the scripted model:
   the tool must be absent before `load_skill` and present after.

5. **Run** `uv run pytest agents/declarative_agent` and `make check`.

No YAML change is needed: the skill toolset loads every folder under `skills/`.

## Review checklist

- Does the description say *when* to use it, and not overlap another skill?
- Is every tool it unlocks guarded by a callback if it can do harm?
- Would the model need the references every time? If yes, move them into the body.
- Is anything in it a rule that must always hold? Then it belongs in a callback, not a skill.
