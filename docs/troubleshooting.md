# Troubleshooting

- `state: superseded`: an exact pinned base/head pair is no longer fetchable. Dispatch the current pair; do not treat the stale run as a candidate failure. This is also the expected neutral result when Release Please or another post-merge producer dispatches a candidate that a newer release commit has already replaced.
- `unknownPaths` is non-empty: add path ownership or ensure fallback domains are intentionally conservative.
- `missing-or-invalid-evidence`: confirm every selected domain uploaded evidence from the same repository, run ID, base, head, and fingerprint.
- configuration errors: run `vv doctor`; duplicate IDs, missing dependencies, cycles, unsafe working directories, and shell-string commands fail closed.
- action does not start: inspect the GitHub job annotation separately from validation output. Runner/account failures are not domain failures.
