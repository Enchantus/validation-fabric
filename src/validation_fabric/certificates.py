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
    plan: dict[str, Any], evidence: list[dict[str, Any]], repository: str, run_id: int, key: str
) -> dict[str, Any]:
    expected = {item["domain"]: item["fingerprint"] for item in plan.get("domains", [])}
    accepted: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    for item in evidence:
        domain_value = item.get("domain")
        domain = domain_value if isinstance(domain_value, str) else ""
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
    for domain in expected:
        if domain not in accepted:
            failures.append({"kind": "missing-or-invalid-evidence", "domain": domain})
    payload = {
        "repository": repository,
        "runId": run_id,
        "base": plan.get("base"),
        "head": plan.get("head"),
        "admitted": not failures and plan.get("state") == "planned",
        "failures": failures,
        "evidenceDigests": {
            domain: hashlib.sha256(canonical(item)).hexdigest() for domain, item in sorted(accepted.items())
        },
    }
    return issue_certificate(payload, key)
