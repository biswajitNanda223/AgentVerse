# Concepts

## Declarative vs code-defined agents

| | Declarative (YAML) | Code (Python) |
|---|---|---|
| Define | `root_agent.yaml`: name, model, instruction, tools, sub-agents, callbacks | `LlmAgent(...)` in a module |
| Change a prompt or model | edit text | edit code, usually the same diff size, but a developer's job |
| Review | the whole agent in one short file | spread across modules |
| Limits | cannot pass constructor arguments; references Python by dotted path | anything Python can do |
| ADK status (2.9.2) | experimental | stable |

They are not exclusive. This example is declarative for the parts a person should be able to read
and edit (identity, instruction, wiring) and Python for what must be exact (the guardrails, the
SQL checks, the skill list). A good rule: **declare what you configure, code what you enforce.**

## Skill-based engineering

A skill is a folder an agent can load, following the open Agent Skills layout that ADK implements.
Treat each one like a small piece of software:

- **One job, one owner.** The description says when to use it, so a reviewer can see overlap.
- **Progressive disclosure.** Only the description is always in context; the body and references
  load when needed, which keeps the prompt short as the agent learns more.
- **Testable.** The loader validates the name and frontmatter; the tests check what a skill unlocks.
- **Gates capability.** A skill can list tools it unlocks. Until it is loaded the model cannot
  see them, so a risky tool is opt-in per task instead of always on.
- **Versioned.** Skills are text in git, so a change to expertise is a reviewed diff. ADK can also
  load skills from a cloud storage folder, which would let a skill change without rebuilding the
  container (not exercised here).

## Skills vs tools vs callbacks

| Mechanism | Is | The model | Use for |
|---|---|---|---|
| Tool | a function it can call | chooses when to call it | doing things |
| Skill | instructions (and optionally tool access) | chooses when to load it | knowing how to do things well |
| Callback | code ADK runs around a model or tool call | cannot skip or edit it | rules that must always hold |

## What the guardrails guarantee, and what they do not

Guaranteed by code: the model-call cap, that blocked SQL never executes, that a write is only a
draft, that unlocked tools stay invisible until their skill is loaded. Not guaranteed: that the
model picks the right skill, follows its advice, or writes a good query on the first try. Tests
prove the first group; only live runs with a real model measure the second.

## Where this maps to the Project SLM scenarios

Only these scenarios from the supplied list are implemented here: ADK-02 (model-call circuit
breaker, 45), ADK-07 (deterministic SQL check before tools), GOV-01 (no raw dumps, cited
records), GOV-02 and GOV-05 (allowed tables and masked columns, as defence in depth), BKD-01 and
BKD-04 (draft-only writes with an idempotency key). The rest are out of scope for this example.
