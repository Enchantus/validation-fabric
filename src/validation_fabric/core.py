"""Deterministic risk planning and execution."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Domain, FabricConfig

GENERATED_PARTS = {".git", ".next", ".pytest_cache", ".venv", "__pycache__", "coverage", "node_modules"}


class FabricError(RuntimeError):
    pass


class SupersededRange(FabricError):
    """An explicitly pinned candidate range no longer exists locally."""


@dataclass(frozen=True)
class PlanRecord:
    domain: str
    fingerprint: str
    runner: str
    toolchain: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    schema_version: int
    state: str
    base: str
    head: str
    changed: tuple[str, ...]
    unknown_paths: tuple[str, ...]
    fallback_activated: bool
    domains: tuple[PlanRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["schemaVersion"] = result.pop("schema_version")
        result["unknownPaths"] = result.pop("unknown_paths")
        result["fallbackActivated"] = result.pop("fallback_activated")
        return result


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        fnmatch.fnmatchcase(normalized, pattern)
        or (pattern.startswith("**/") and fnmatch.fnmatchcase(normalized, pattern[3:]))
        for pattern in patterns
    )


def select_domains(changed: list[str], config: FabricConfig) -> tuple[list[str], list[str]]:
    selected: set[str] = set()
    unknown: list[str] = []
    for path in changed:
        owners = {domain.id for domain in config.domains.values() if matches(path, domain.paths)}
        if not owners:
            unknown.append(path)
        selected.update(owners)
    if unknown:
        selected.update(config.fallback_domains)
    pending = list(selected)
    while pending:
        for requirement in config.domains[pending.pop()].requires:
            if requirement not in selected:
                selected.add(requirement)
                pending.append(requirement)
    return sorted(selected), sorted(set(unknown))


def git_changed_paths(root: Path, base: str, head: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", f"{base}...{head}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        pinned = len(base) == 40 and len(head) == 40 and all(char in "0123456789abcdefABCDEF" for char in base + head)
        message = completed.stderr.strip() or "git diff failed"
        if pinned:
            raise SupersededRange(message)
        raise FabricError(message)
    return sorted({line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()})


def _files(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not GENERATED_PARTS.intersection(path.relative_to(root).parts)
        and matches(path.relative_to(root).as_posix(), patterns)
    )


def fingerprint(root: Path, config: FabricConfig, domain: Domain, changed: list[str]) -> str:
    relevant = {path for path in changed if matches(path, domain.paths)}
    material = {
        "schemaVersion": config.schema_version,
        "domain": domain.id,
        "commands": domain.commands,
        "cwd": domain.cwd,
        "runner": domain.runner,
        "toolchain": domain.toolchain,
        "requires": domain.requires,
        "changed": {path: _digest(root / path) if (root / path).is_file() else "deleted" for path in sorted(relevant)},
        "inputs": {path.relative_to(root).as_posix(): _digest(path) for path in _files(root, domain.inputs)},
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_plan(root: Path, config: FabricConfig, base: str, head: str) -> Plan:
    try:
        changed = git_changed_paths(root, base, head)
    except SupersededRange:
        return Plan(1, "superseded", base, head, (), (), False, ())
    selected, unknown = select_domains(changed, config)
    records = tuple(
        PlanRecord(
            domain_id,
            fingerprint(root, config, config.domains[domain_id], changed),
            config.domains[domain_id].runner,
            config.domains[domain_id].toolchain,
        )
        for domain_id in selected
    )
    return Plan(
        1, "planned", base, head, tuple(changed), tuple(unknown), bool(unknown and config.fallback_domains), records
    )


def run_domain(root: Path, domain: Domain, changed: tuple[str, ...]) -> tuple[int, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    relevant = [path for path in changed if matches(path, domain.paths)]
    for command in domain.commands:
        argv = [item for argument in command for item in (relevant if argument == "{changed}" else [argument])]
        completed = subprocess.run(argv, cwd=root / domain.cwd, check=False, capture_output=True)
        results.append(
            {
                "argv": argv,
                "exitCode": completed.returncode,
                "stdoutDigest": hashlib.sha256(completed.stdout).hexdigest(),
                "stderrDigest": hashlib.sha256(completed.stderr).hexdigest(),
            }
        )
        if completed.returncode:
            return completed.returncode, results
    return 0, results
