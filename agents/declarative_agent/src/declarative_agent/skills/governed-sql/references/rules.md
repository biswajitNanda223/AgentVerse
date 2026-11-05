# Governed SQL rules

| Rule | Why |
|---|---|
| Single SELECT only | An LLM-written query must never change data or chain statements |
| Explicit columns | Keeps masked or commercial columns from leaking through `*` |
| Allowed tables only | A user must never query another business unit's shared data |
| No masked columns | Unit prices and vendor bid margins are hidden from some roles |
| LIMIT 20 or aggregate | Blocks raw table dumps while still serving curated evidence |

Blocked requests return `{"blocked": true, "reason": "..."}`. They are never silently rewritten.
