# Configuration reference

Consumers commit `.validation-fabric.yml` at the repository root.

- `schemaVersion`: currently `1`.
- `defaultBranch`: the protected integration branch; it is not assumed to be `main`.
- `fallbackDomains`: domains selected whenever a changed path has no owner.
- `domains`: ordered domain definitions with `id`, `paths`, `inputs`, `commands`, optional `requires`, `cwd`, `runner`, and `toolchain`.
- `merge`: optional `enabled`, `method`, `admissionCheck`, and `postMergeWorkflows`. It defaults off.

Commands are argv arrays, not shell strings. Use the special argument `{changed}` to expand paths owned by that domain. Working directories must stay inside the repository. Dependencies must exist and form an acyclic graph.

Unknown paths are reported and widen validation. They are not automatic failures when every conservative fallback domain produces valid evidence.
