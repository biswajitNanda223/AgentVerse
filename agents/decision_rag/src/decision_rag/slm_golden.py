"""Questions over the Project SLM scenario catalogue, each mapped to the scenario that answers it.

The scenarios are only those in the supplied text (Domains 1 to 7). The questions are written
from that text; `expected` is the scenario id whose section title starts with `[ID]`.
"""

GOLDEN_SLM: list[tuple[str, str]] = [
    ("What stops an agent from looping forever and burning tokens on one question?", "[ADK-02]"),
    ("How does a user cancel a running query after typing the wrong site name?", "[ADK-03]"),
    ("How do we block DDL statements and raw table scans in LLM-generated SQL?", "[ADK-07]"),
    ("What happens when the primary reasoning model hits a quota spike?", "[ADK-06]"),
    ("How do we attribute token spend to each business unit for finance?", "[TEL-02]"),
    ("How do we keep confidential commercial values out of trace logs?", "[TEL-05]"),
    ("What prevents a user from querying another BU's shared data over Delta Sharing?", "[GOV-02]"),
    ("How are unit prices masked for a site planning engineer?", "[GOV-05]"),
    ("How do we avoid a 413 error when a contracts manager uploads a 35 MB PDF?", "[VEC-01]"),
    ("When do abandoned session uploads and temporary vectors get purged?", "[VEC-07]"),
    (
        "What guarantees that a double-clicked approve does not create duplicate records?",
        "[BKD-04]",
    ),
    ("How do we avoid a cold start for the first executives logging in before nine?", "[SCL-07]"),
    ("Can the app resume the answer after a short cellular network blip on site?", "[UX-06]"),
]
