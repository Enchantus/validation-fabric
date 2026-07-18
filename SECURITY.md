# Security policy

Report vulnerabilities through GitHub's private security-advisory interface for this repository. Do not open a public issue for an undisclosed vulnerability.

Supported security fixes target the latest released major version. Prereleases receive fixes on a best-effort basis until `v1.0.0`.

The primary invariant is that pull-request-controlled code never receives an admission signing key, package publishing identity, or merge authority. See [the security model](docs/security-model.md).
