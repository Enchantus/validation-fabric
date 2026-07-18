"""Consumer configuration for Validation Fabric."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a consumer manifest violates the public schema."""


@dataclass(frozen=True)
class Domain:
    id: str
    paths: tuple[str, ...]
    inputs: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...]
    requires: tuple[str, ...] = ()
    cwd: str = "."
    runner: str = "ubuntu-latest"
    toolchain: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeConfig:
    enabled: bool = False
    method: str = "squash"
    admission_check: str = "Validation Fabric / admission"
    post_merge_workflows: tuple[str, ...] = ()


@dataclass(frozen=True)
class FabricConfig:
    schema_version: int
    default_branch: str
    fallback_domains: tuple[str, ...]
    domains: dict[str, Domain]
    merge: MergeConfig = MergeConfig()


def _strings(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"{field_name} must be a list of non-empty strings")
    return tuple(value)


def _commands(value: Any, field_name: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field_name} must contain at least one argv list")
    commands: list[tuple[str, ...]] = []
    for command in value:
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            raise ConfigError(f"{field_name} commands must be non-empty argv lists")
        commands.append(tuple(command))
    return tuple(commands)


def load_config(path: Path | str = ".validation-fabric.yml") -> FabricConfig:
    manifest = Path(path)
    if not manifest.is_file():
        raise ConfigError(f"configuration not found: {manifest}")
    raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")
    if raw.get("schemaVersion") != 1:
        raise ConfigError("schemaVersion must be 1")
    default_branch = raw.get("defaultBranch", "main")
    if not isinstance(default_branch, str) or not default_branch:
        raise ConfigError("defaultBranch must be a non-empty string")
    raw_domains = raw.get("domains")
    if not isinstance(raw_domains, list) or not raw_domains:
        raise ConfigError("domains must contain at least one domain")
    domains: dict[str, Domain] = {}
    for index, item in enumerate(raw_domains):
        prefix = f"domains[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{prefix} must be a mapping")
        domain_id = item.get("id")
        if not isinstance(domain_id, str) or not domain_id:
            raise ConfigError(f"{prefix}.id must be a non-empty string")
        if domain_id in domains:
            raise ConfigError(f"duplicate domain id: {domain_id}")
        cwd = item.get("cwd", ".")
        runner = item.get("runner", "ubuntu-latest")
        toolchain = item.get("toolchain", {})
        if not isinstance(cwd, str) or Path(cwd).is_absolute() or ".." in Path(cwd).parts:
            raise ConfigError(f"{prefix}.cwd must stay within the repository")
        if not isinstance(runner, str) or not runner:
            raise ConfigError(f"{prefix}.runner must be a non-empty string")
        if not isinstance(toolchain, dict):
            raise ConfigError(f"{prefix}.toolchain must be a mapping")
        domains[domain_id] = Domain(
            id=domain_id,
            paths=_strings(item.get("paths"), f"{prefix}.paths"),
            inputs=_strings(item.get("inputs"), f"{prefix}.inputs"),
            commands=_commands(item.get("commands"), f"{prefix}.commands"),
            requires=_strings(item.get("requires"), f"{prefix}.requires"),
            cwd=cwd,
            runner=runner,
            toolchain=toolchain,
        )
    fallback = _strings(raw.get("fallbackDomains"), "fallbackDomains")
    unknown_ids = sorted(
        {item for domain in domains.values() for item in domain.requires if item not in domains}
        | {item for item in fallback if item not in domains}
    )
    if unknown_ids:
        raise ConfigError(f"unknown domain references: {', '.join(unknown_ids)}")
    _assert_acyclic(domains)
    merge_raw = raw.get("merge", {})
    if not isinstance(merge_raw, dict):
        raise ConfigError("merge must be a mapping")
    method = merge_raw.get("method", "squash")
    if method not in {"merge", "squash", "rebase"}:
        raise ConfigError("merge.method must be merge, squash, or rebase")
    return FabricConfig(
        schema_version=1,
        default_branch=default_branch,
        fallback_domains=fallback,
        domains=domains,
        merge=MergeConfig(
            enabled=bool(merge_raw.get("enabled", False)),
            method=method,
            admission_check=str(merge_raw.get("admissionCheck", "Validation Fabric / admission")),
            post_merge_workflows=_strings(merge_raw.get("postMergeWorkflows"), "merge.postMergeWorkflows"),
        ),
    )


def _assert_acyclic(domains: dict[str, Domain]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(domain_id: str) -> None:
        if domain_id in visiting:
            raise ConfigError(f"domain dependency cycle includes: {domain_id}")
        if domain_id in visited:
            return
        visiting.add(domain_id)
        for requirement in domains[domain_id].requires:
            visit(requirement)
        visiting.remove(domain_id)
        visited.add(domain_id)

    for domain_id in domains:
        visit(domain_id)
