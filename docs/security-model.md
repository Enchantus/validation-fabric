# Security and trust model

Validation Fabric has two planes.

1. The pull-request plane is entered through a `pull_request_target` caller committed to the protected default branch. It checks out candidate code, loads validation policy from the exact trusted base commit, removes checkout credentials, executes those commands, and uploads unsigned evidence. It receives read-only repository permissions and no privileged secret. Fork heads are checked out from their source repository while the base manifest and base commit are fetched from the consumer repository.
2. The admission plane is invoked by a caller committed to the protected default branch. It re-reads the originating workflow run, checks repository, workflow name and path, run, base, head repository, head SHA, and PR identity, recomputes the exact plan from the same base manifest, validates every evidence fingerprint, rejects duplicate or unexpected evidence, and only then signs admission.

Evidence is not authority. A signature is valid only for its exact certificate payload. A successful domain job alone is insufficient for admission.

Threats explicitly covered by tests include moved PR heads, stale bases, altered evidence, wrong run or repository identity, missing domains, invalid signatures, dependency cycles, unknown paths, cancelled jobs, and cache substitution. GitHub artifact attestations and release OIDC protect distribution separately from candidate admission.

Consumers must never call the privileged workflow from a PR-controlled workflow or pass its key to the reusable validation workflow. The example `workflow_run` caller resolves the open pull request through the API because GitHub may return an empty `workflow_run.pull_requests` array even for a pull-request run.

The optional merge workflow is a separate privileged plane. It downloads the admission certificate from an explicitly identified admission run, verifies its signature and repository/head identity, requires exactly one successful configured admission check on that same head, and then re-reads the open PR, default-branch SHA, admitted head, and mergeability before submitting a SHA-bound merge.
