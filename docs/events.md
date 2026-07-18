# Event ledger

Validation Fabric can retain candidate lifecycle events as one immutable JSON
file per event ID. Writers publish through an atomic filesystem link: the first
payload for an ID wins, an exact retry is idempotent, and a different payload
with the same ID fails closed.

```bash
vv event candidate.created --event-id run-42-created --candidate HEAD \
  --occurred-at 2026-01-01T00:00:00Z
vv event domain.completed --event-id run-42-python --candidate HEAD \
  --domain python --occurred-at 2026-01-01T00:02:00Z
vv status --event-dir .validation-fabric/events --candidate HEAD
```

Automation should derive event IDs from stable run and transition identities,
not timestamps alone. Event metadata is optional and must remain sanitized;
never place credentials, private logs, or customer data in the ledger.

The reducer orders by `occurredAt` and `eventId`, scopes every result to one
candidate, and emits a versioned JSON status containing the candidate state,
latest state per domain, and accepted event count.
