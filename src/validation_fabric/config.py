"""Configuration parsing and validation for .validation-fabric.yml."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Domain:
    """A domain with required validations."""
    name: str
    description: str = ""
    required_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Config:
    """Validation Fabric configuration."""
    version: str
    domains: dict[str, Domain] = field(default_factory=dict)
    transitive_requirements: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: Path | str) -> Config:
        """Parse configuration from a YAML file."""
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        version = data.get("version", "1.0")
        if not isinstance(version, str):
            raise ValueError(f"Invalid version format: {version}")

        domains_data = data.get("domains", {})
        if not isinstance(domains_data, dict):
            raise ValueError("domains must be a dictionary")

        domains = {}
        for domain_name, domain_spec in domains_data.items():
            if isinstance(domain_spec, dict):
                domains[domain_name] = Domain(
                    name=domain_name,
                    description=domain_spec.get("description", ""),
                    required_checks=domain_spec.get("required_checks", []),
                )
            else:
                raise ValueError(f"Invalid domain specification for {domain_name}")

        transitive_reqs = data.get("transitive_requirements", {})
        if not isinstance(transitive_reqs, dict):
            raise ValueError("transitive_requirements must be a dictionary")

        return cls(
            version=version,
            domains=domains,
            transitive_requirements=transitive_reqs,
        )

    def to_json(self) -> str:
        """Serialize configuration to schema-versioned JSON."""
        data = {
            "schema_version": self.version,
            "domains": {name: domain.to_dict() for name, domain in self.domains.items()},
            "transitive_requirements": self.transitive_requirements,
        }
        return json.dumps(data, indent=2, sort_keys=True)

    def fingerprint(self) -> str:
        """Generate a deterministic SHA256 fingerprint of the configuration."""
        json_str = self.to_json()
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def select_domains(self, domain_names: list[str] | None = None) -> dict[str, Domain]:
        """Select specific domains or all if none specified."""
        if domain_names is None:
            return self.domains

        selected = {}
        for name in domain_names:
            if name not in self.domains:
                raise ValueError(f"Unknown domain: {name}")
            selected[name] = self.domains[name]
        return selected

    def get_transitive_requirements(self, domain_name: str) -> list[str]:
        """Get all transitive requirements for a domain."""
        if domain_name not in self.transitive_requirements:
            return []
        return self.transitive_requirements[domain_name]
