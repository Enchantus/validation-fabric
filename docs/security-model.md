# Security and trust model

Validation Fabric has two planes.

1. The pull-request plane checks out candidate code, selects domains, executes configured commands, and uploads unsigned evidence. It receives read-only repository permissions and no privileged credential.
2. The admission plane is invoked by a caller committed to the protected default branch. It re-reads the originating workflow run, checks repository/run/base/head/PR identity, recomputes the exact plan, validates every evidence fingerprint, and only then signs admission.

Evidence is not authority. A signature is valid only for its exact certificate payload. A successful domain job alone is insufficient for admission.

Threats explicitly covered by tests include moved PR heads, stale bases, altered evidence, wrong run or repository identity, missing domains, invalid signatures, dependency cycles, unknown paths, cancelled jobs, and cache substitution. GitHub artifact attestations and release OIDC protect distribution separately from candidate admission.

Consumers must never call the privileged workflow from a PR-controlled workflow or pass its key to the reusable validation workflow.

The optional merge workflow is a separate privileged plane and should be called only after the admission job succeeds. It re-reads the open PR, default-branch SHA, admitted head, and mergeability before submitting a SHA-bound merge.
