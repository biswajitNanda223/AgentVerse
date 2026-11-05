---
name: loop-and-budget-discipline
description: Use when a request is ambiguous, when tools keep returning empty or conflicting results, or when you notice you are repeating the same step. Explains how to stop looping and ask or summarise instead.
license: Apache-2.0
---

# Loop and budget discipline

A runtime guard stops any single question after a fixed number of model calls. Do not rely on it:
stop yourself first.

1. If the request is ambiguous (for example two possible projects or sites), ask one short
   clarifying question instead of trying both.
2. If a step returns nothing useful twice in a row, stop repeating it. Change the approach or say
   what is missing.
3. Never call the same tool with the same arguments twice in one answer.
4. When you are close to giving up, give a partial answer from the evidence you have, state what
   is missing, and stop.
