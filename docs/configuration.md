# Configuration reference

Consumers commit `.validation-fabric.yml` at the repository root.

- `schemaVersion`: currently `1`.
- `defaultBranch`: the protected integration branch; it is not assumed to be `main`.
- `fallbackDomains`: domains selected whenever a changed path has no owner.
- `domains`: ordered domain definitions with `id`, `paths`, `inputs`, `commands`, optional `requires`, `cwd`, `runner`, and `toolchain`.
- `merge`: optional `enabled`, `method`, `admissionCheck`, and `postMergeWorkflows`. It defaults off.

Commands are argv arrays, not shell strings. Use the special argument `{changed}` to expand paths owned by that domain. Working directories must stay inside the repository. Dependencies must exist and form an acyclic graph.

The GitHub Action recognizes `python`, `uv`, `node`, and `go` keys in a
domain's `toolchain` mapping. Dependency installation remains an explicit
domain command (for example, `uv sync --locked` or `npm ci`) so the same plan
has equivalent behavior locally and in hosted CI.

Unknown paths are reported and widen validation. They are not automatic failures when every conservative fallback domain produces valid evidence.

## Change-impact contract

`vv impact --base <base> --head <head>` emits a reusable JSON contract for
local update loops and cross-project validation planning. It keeps admission
strict while helping operators avoid repeated proof:

- selected domains without matching green evidence appear in `localDomains`;
- selected domains with the same fingerprint as prior passing evidence appear
  in `carriedDomains`;
- unchanged domains and carried-forward domains are written to `skippedGates`;
- `githubCi` is `skip` unless a named acceptance checkpoint is provided.

Matching green evidence is evidence with schema version `1`, result `pass`, and
the same domain fingerprint. The fingerprint already includes the domain
commands, inputs, changed content, runner, toolchain, dependencies, and manifest
schema, so the carry-forward decision is invalidated when any of those
preconditions change.

Use `--evidence-dir <path>` to make prior local evidence available. Use
`--checkpoint shared-contract`, `--checkpoint merge`, `--checkpoint release`,
`--checkpoint deployment`, or `--checkpoint live-proof` to explicitly escalate
from minimum local proof to hosted or integration proof. Other checkpoint names
are recorded but do not escalate by themselves.

The impact contract is planning evidence, not an admission certificate. The
privileged admission workflow still re-computes the exact plan and requires
exact-candidate evidence before signing admission.

The `updateProtocol` object is intentionally stable for operator update loops:
it marks that progress reporting, minimum-proof selection, carry-forward
evidence, skipped-gate records, and CI de-duplication are active for the current
contract.
