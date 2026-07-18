# Changelog

This project follows Semantic Versioning and Keep a Changelog.

## [Unreleased]

### Fixed

- Make every `vv init` language preset generate its documented domain and toolchain shape.
- Keep the public prerelease status synchronized with the latest protected release.
- Turn every language example into an executable clean-consumer fixture and run all four through `doctor`, `plan`, and `run` in CI.

### Security

- Require byte-for-byte reproducible distributions and a clean-wheel quick-start smoke test in CI and release jobs.
- Document adversaries, trust boundaries, fail-closed controls, residual risk, and the exact consumer rollback boundary.

## [0.2.0a3] - 2026-07-18

### Fixed

- Bind supported pull-request source runs to the exact candidate SHA reported by the Actions run API.

## [0.2.0a2] - 2026-07-18

### Fixed

- Verify configured workflow identity through the source run's `workflow_id` when callers use a dynamic `run-name`.
- Report the installed package version through `vv --version` and keep the package version constant synchronized.

## [0.2.0a1] - 2026-07-18

### Added

- Atomic, idempotent lifecycle event ledger and deterministic candidate status reduction.
- Fork-aware fixture coverage for alternate branches, renamed and deleted paths, empty ranges, and unknown files.

### Security

- Load validation and admission policy from the exact trusted base commit.
- Bind run identity to repository, workflow path, event, head repository, PR, base, and head.
- Require a signed PR-bound certificate and exact successful admission check before optional merging.
- Remove checkout credentials before candidate commands and pin every external Action to an immutable commit.
- Reject duplicate, malformed, unexpected, mismatched, missing, and stale evidence.
- Preserve independently downloaded evidence files so duplicate-domain submissions fail closed.
- Skip privileged admission for superseded source ranges without reporting a candidate failure.

## [0.1.0a1] - 2026-07-18

### Added

- Generic package, `vv` CLI, consumer manifest, risk planning, evidence, and certificate APIs.
- Unprivileged validation and privileged admission reusable workflows.
- Opt-in exact-candidate merge controller.
