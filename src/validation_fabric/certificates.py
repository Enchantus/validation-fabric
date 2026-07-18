"""Evidence envelopes and privileged admission certificates."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class Evidence:
    schema_version: int
    repository: str
    run_id: int
    base: str
    head: str
    domain: str
    fingerprint: str
    result: str
    commands: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "repository": self.repository,
            "runId": self.run_id,
            "base": self.base,
            "head": self.head,
            "domain": self.domain,
            "fingerprint": self.fingerprint,
            "result": self.result,
            "commands": list(self.commands),
        }


def issue_certificate(payload: dict[str, Any], key: str) -> dict[str, Any]:
    if not key:
        raise ValueError("certificate key is required")
    certificate = {**payload, "schemaVersion": 1, "issuedAt": datetime.now(UTC).isoformat()}
    return {
        "certificate": certificate,
        "signature": hmac.new(key.encode(), canonical(certificate), hashlib.sha256).hexdigest(),
    }


def verify_certificate(envelope: dict[str, Any], key: str) -> bool:
    certificate = envelope.get("certificate")
    signature = envelope.get("signature")
    if not isinstance(certificate, dict) or not isinstance(signature, str) or not key:
        return False
    expected = hmac.new(key.encode(), canonical(certificate), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def admit(
    plan: dict[str, Any],
    evidence: list[Any],
    repository: str,
    run_id: int,
    key: str,
    pull_request: int = 0,
) -> dict[str, Any]:
    expected = {item["domain"]: item["fingerprint"] for item in plan.get("domains", [])}
    accepted: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for item in evidence:
        if not isinstance(item, dict):
            failures.append({"kind": "malformed-evidence", "domain": ""})
            continue
        domain_value = item.get("domain")
        domain = domain_value if isinstance(domain_value, str) else ""
        counts[domain] = counts.get(domain, 0) + 1
        if domain not in expected:
            failures.append({"kind": "unexpected-evidence", "domain": domain})
            continue
        if (
            domain in expected
            and item.get("schemaVersion") == 1
            and item.get("repository") == repository
            and item.get("runId") == run_id
            and item.get("base") == plan.get("base")
            and item.get("head") == plan.get("head")
            and item.get("fingerprint") == expected[domain]
            and item.get("result") == "pass"
        ):
            accepted[domain] = item
    for domain, count in sorted(counts.items()):
        if count > 1:
            accepted.pop(domain, None)
            failures.append({"kind": "duplicate-evidence", "domain": domain})
    for domain in expected:
        if domain not in accepted:
            failures.append({"kind": "missing-or-invalid-evidence", "domain": domain})
    payload = {
        "repository": repository,
        "runId": run_id,
        "pullRequest": pull_request,
        "base": plan.get("base"),
        "head": plan.get("head"),
        "admitted": not failures and plan.get("state") == "planned",
        "failures": failures,
        "evidenceDigests": {
            domain: hashlib.sha256(canonical(item)).hexdigest() for domain, item in sorted(accepted.items())
        },
    }
    return issue_certificate(payload, key)


def authorize_merge_certificate(
    envelope: dict[str, Any], key: str, repository: str, head: str, pull_request: int
) -> dict[str, Any]:
    if not verify_certificate(envelope, key):
        return {"authorized": False, "reason": "invalid-certificate"}
    certificate = envelope["certificate"]
    checks = {
        "schemaVersion": certificate.get("schemaVersion") == 1,
        "admitted": certificate.get("admitted") is True,
        "repository": certificate.get("repository") == repository,
        "head": certificate.get("head") == head,
        "pullRequest": certificate.get("pullRequest") == pull_request,
        "base": isinstance(certificate.get("base"), str) and bool(certificate.get("base")),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        return {"authorized": False, "reason": "certificate-identity-mismatch", "failures": failed}
    return {"authorized": True, "base": certificate["base"]}
