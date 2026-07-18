# Threat model

## Assets and security objectives

Validation Fabric protects the integrity of validation evidence, admission certificates, required-check decisions, merge authority, and release artifacts. Its central objective is that code controlled by a pull request cannot grant itself trusted admission or obtain privileged credentials.

## Trust boundaries

- **Candidate plane:** checks out and executes the candidate with read-only repository access. Its evidence is always unsigned and untrusted.
- **Default-branch verifier:** executes only workflow code from the consumer's protected default branch, resolves the originating run and open pull request, recomputes the trusted plan, and signs an exact-identity certificate.
- **Optional merge plane:** consumes a signed certificate and rechecks the current pull request, admitted head, default branch, configured admission check, and mergeability. It is disabled unless the consumer manifest opts in.
- **Release plane:** builds from a protected tag, proves byte-identical artifacts, attests them, and publishes through GitHub OIDC only when the PyPI publication gate is enabled.

## Adversaries and controls

| Threat | Fail-closed control |
| --- | --- |
| A pull request changes its manifest or caller to weaken validation | Validation and admission load the manifest from the exact trusted base commit; callers run from the default branch. |
| Candidate code reads a signing, publishing, or merge credential | Candidate jobs receive read-only permissions and no privileged environment or reusable-workflow secret. |
| Evidence is missing, duplicated, altered, replayed, or substituted from another run | Admission binds repository, source run, pull request, base, head, domain, and deterministic fingerprint and rejects unexpected or duplicate evidence. |
| A source run uses an unexpected workflow, event, title, repository, or candidate | The verifier rereads both the Actions run and workflow object and checks every configured identity field. |
| A candidate moves after validation | Admission requires the exact open base/head pair; merge repeats the head and base checks immediately before mutation. |
| A stale Release Please or post-merge dispatch arrives after its range disappears | Planning and merge classify the exact missing or replaced range as `superseded`, a neutral terminal state. |
| A cache returns results for different inputs or commands | Fingerprints cover configuration, changed content, transitive inputs, commands, working directory, runner, and toolchain. |
| A fork attempts to impersonate the base repository | Source and pull-request identity checks bind the candidate head repository separately from the protected base repository. |
| A dependency or Action tag changes after review | Repository-owned workflows pin third-party Actions to immutable commits; consumers may pin Validation Fabric to a release commit. |
| Release bytes differ across builds or are replaced after tagging | CI and release build twice under a fixed epoch, compare bytes, smoke-install the wheel, and attest published artifacts. |

## Availability and residual risk

GitHub Actions, package indexes, runners, and consumer toolchains remain external availability dependencies. Runner or account failures are operational failures, not candidate validation failures. The HMAC certificate key is consumer-managed; compromise requires rotation and invalidation of certificates from the affected window. Validation Fabric does not make arbitrary consumer commands safe—it isolates their authority and binds their results to exact inputs.

Security-sensitive changes require tests at the boundary they modify and review against this model and [the implementation security model](security-model.md).
