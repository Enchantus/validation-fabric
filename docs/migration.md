# Migration and rollback

Adopt in shadow mode first:

1. Commit a manifest that represents existing validation ownership.
2. Run legacy CI and Validation Fabric for identical base/head pairs.
3. Compare changed paths, selected domains, unknown paths, fingerprints, command outcomes, and admissions.
4. Expand ownership or fallback domains for every unexplained legacy-only failure.
5. Require admission only after sustained parity.

Keep the legacy workflow manually dispatchable for one observation window. Roll back by removing admission from required checks and restoring the legacy PR caller; certificates and evidence are diagnostic and do not mutate source state.

SessionBuddie is the first compatibility consumer and will use this dual-proof process before removing its embedded implementation.
