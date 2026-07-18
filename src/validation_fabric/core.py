"""Core validation logic and requirement resolution."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Any

from .config import Config, Domain


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    domain: str
    passed: bool
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainPlan:
    """Execution plan for a domain's validations."""
    domain_name: str
    required_checks: list[str]
    transitive_requirements: list[str]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RequirementResolver:
    """Resolves and tracks transitive requirements."""

    def __init__(self, config: Config):
        self.config = config
        self._resolved_cache: dict[str, set[str]] = {}

    def resolve_all_requirements(self, domain_name: str) -> set[str]:
        """Recursively resolve all transitive requirements for a domain."""
        if domain_name in self._resolved_cache:
            return self._resolved_cache[domain_name]

        requirements: set[str] = set()
        direct = self.config.get_transitive_requirements(domain_name)

        for req in direct:
            requirements.add(req)
            transitive = self.resolve_all_requirements(req)
            requirements.update(transitive)

        self._resolved_cache[domain_name] = requirements
        return requirements

    def create_plan(self, domain_name: str) -> DomainPlan:
        """Create an execution plan for validating a domain."""
        if domain_name not in self.config.domains:
            raise ValueError(f"Unknown domain: {domain_name}")

        domain = self.config.domains[domain_name]
        transitive = self.resolve_all_requirements(domain_name)

        plan_data = {
            "domain": domain_name,
            "required_checks": domain.required_checks,
            "transitive_requirements": sorted(transitive),
        }
        fingerprint = hashlib.sha256(
            json.dumps(plan_data, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return DomainPlan(
            domain_name=domain_name,
            required_checks=domain.required_checks,
            transitive_requirements=sorted(transitive),
            fingerprint=fingerprint,
        )
