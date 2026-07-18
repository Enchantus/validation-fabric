# Release policy

Releases use SemVer. Major workflow tags such as `v1` may advance only within their major line; consumers needing immutability may pin a full tag or commit SHA.

A release requires the Python matrix, tests, lint, package build, action validation, fixture adoption, security review, and provenance attestation. PyPI publication uses GitHub OIDC trusted publishing and an environment named `pypi`; no long-lived upload token belongs in repository secrets.

Every tag publishes the attested wheel and source archive to a GitHub Release.
PyPI publication is fail-closed behind the repository variable
`PYPI_PUBLISH_ENABLED=true`; enable it only after the matching PyPI trusted
publisher has been configured for the `pypi` environment.

`v1.0.0` additionally requires SessionBuddie shadow parity with no unexplained divergence and a tested rollback.
