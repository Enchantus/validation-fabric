# Release policy

Releases use SemVer. Major workflow tags such as `v1` may advance only within their major line; consumers needing immutability may pin a full tag or commit SHA.

A release requires the Python matrix, tests, lint, two byte-identical package builds under the recorded `SOURCE_DATE_EPOCH`, canonically compressed source archives, a clean-wheel quick-start smoke test, action validation, fixture adoption, security review, and provenance attestation. PyPI publication uses GitHub OIDC trusted publishing and an environment named `pypi`; no long-lived upload token belongs in repository secrets.

Every tag publishes the attested wheel and source archive to a GitHub Release.
PyPI publication is fail-closed behind the repository variable
`PYPI_PUBLISH_ENABLED=true`; enable it only after the matching PyPI trusted
publisher has been configured for the `pypi` environment.

Release tags are immutable. After `vX.Y.Z` succeeds and its clean PyPI install is verified, move the corresponding major tag (for example `v1`) to that exact protected release commit and push it with force-with-lease. Never move a full SemVer tag. Record both refs and the release workflow run in the release issue.

`v1.0.0` additionally requires SessionBuddie shadow parity with no unexplained divergence and a tested rollback.
