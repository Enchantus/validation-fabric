"""Evidence collection and certificate generation for admissions."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from .core import ValidationResult


@dataclass
class Evidence:
    """Evidence from a validation check."""
    check_name: str
    domain: str
    timestamp: str
    passed: bool
    details: str = ""

    @staticmethod
    def from_result(result: ValidationResult, timestamp: str | None = None) -> Evidence:
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        return Evidence(
            check_name=result.check_name,
            domain=result.domain,
            timestamp=timestamp,
            passed=result.passed,
            details=result.details,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Certificate:
    """Admission certificate for a domain."""
    domain: str
    admitted: bool
    config_fingerprint: str
    evidence: list[Evidence] = field(default_factory=list)
    certificate_id: str = ""
    issued_at: str = ""

    def __post_init__(self):
        if not self.issued_at:
            self.issued_at = datetime.utcnow().isoformat()
        if not self.certificate_id:
            self.certificate_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate a deterministic certificate ID."""
        data = {
            "domain": self.domain,
            "admitted": self.admitted,
            "issued_at": self.issued_at,
            "config_fingerprint": self.config_fingerprint,
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]

    def add_evidence(self, evidence: Evidence) -> None:
        """Add evidence to the certificate."""
        self.evidence.append(evidence)
        self.certificate_id = self._generate_id()

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "admitted": self.admitted,
            "config_fingerprint": self.config_fingerprint,
            "certificate_id": self.certificate_id,
            "issued_at": self.issued_at,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    def to_json(self) -> str:
        """Serialize certificate to schema-versioned JSON."""
        data = {
            "schema_version": "1.0",
            "certificate": self.to_dict(),
        }
        return json.dumps(data, indent=2, sort_keys=True)
