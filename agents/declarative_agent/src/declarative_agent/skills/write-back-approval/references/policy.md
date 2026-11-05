# Write-back policy

- A draft is not a change. Only an authorized human approving it makes the change.
- The draft id is an idempotency key: the same system, record, field and value always give the
  same id.
- Supported systems: SAP, Primavera, Clapia.
- Before and after values are recorded for the audit trail when a human approves.
