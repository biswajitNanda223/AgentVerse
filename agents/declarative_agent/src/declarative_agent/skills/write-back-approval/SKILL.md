---
name: write-back-approval
description: Use when the user asks you to update a milestone forecast, create an action item or otherwise change a record in SAP, Primavera or Clapia. Unlocks stage_write_back, which only drafts the change for human approval.
license: Apache-2.0
metadata:
  adk_additional_tools:
    - stage_write_back
---

# Write-back approval

You never change an enterprise record yourself. `stage_write_back` only records a **draft**.

1. Confirm the system (SAP, Primavera or Clapia), the record id, the field and the new value with
   the user if any of them is unclear.
2. Call `stage_write_back` once. It returns `status: awaiting_approval` and a `draft_id`.
3. Tell the user the draft is waiting for an authorized human to click Approve, and quote the
   draft id. Do not say the change was made.
4. Calling it again with the same details returns the same draft id, so a double click or a retry
   cannot create a duplicate. Do not try to submit a changed copy to work around that.

See `references/policy.md`.
