"""Change-impact validation contract generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import FabricConfig
from .core import Plan

ACCEPTANCE_CHECKPOINTS = frozenset({"shared-contract", "merge", "release", "deployment", "live-proof"})


@dataclass(frozen=True)
class CarriedEvidence:
    domain: str
    fingerprint: str
    evidence_digest: str
    source_base: str
    source_head: str
    source_run_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "fingerprint": self.fingerprint,
            "evidenceDigest": self.evidence_digest,
            "sourceBase": self.source_base,
            "sourceHead": self.source_head,
            "sourceRunId": self.source_run_id,
        }


@dataclass(frozen=True)
class ImpactDomain:
    domain: str
    fingerprint: str
    decision: str
    reason: str
    runner: str
    toolchain: dict[str, Any]
    carried_evidence: CarriedEvidence | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        carried = result.pop("carried_evidence")
        result["carriedEvidence"] = self.carried_evidence.to_dict() if carried is not None else None
        return result


@dataclass(frozen=True)
class SkippedGate:
    gate: str
    reason: str
    domain: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactContract:
    schema_version: int
    state: str
    base: str
    head: str
    acceptance_checkpoints: tuple[str, ...]
    escalation: str
    domains: tuple[ImpactDomain, ...]
    skipped_gates: tuple[SkippedGate, ...]
    local_domains: tuple[str, ...]
    carried_domains: tuple[str, ...]
    github_ci: str
    github_ci_reason: str
    update_protocol: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "state": self.state,
            "base": self.base,
            "head": self.head,
            "acceptanceCheckpoints": list(self.acceptance_checkpoints),
            "escalation": self.escalation,
            "domains": [domain.to_dict() for domain in self.domains],
            "skippedGates": [gate.to_dict() for gate in self.skipped_gates],
            "localDomains": list(self.local_domains),
            "carriedDomains": list(self.carried_domains),
            "githubCi": self.github_ci,
            "githubCiReason": self.github_ci_reason,
            "updateProtocol": self.update_protocol,
        }


def build_impact_contract(
    plan: Plan,
    config: FabricConfig,
    evidence_dir: Path | None = None,
    checkpoints: tuple[str, ...] = (),
) -> ImpactContract:
    carried = _load_carried_evidence(evidence_dir)
    selected = {record.domain for record in plan.domains}
    checkpoint_names = tuple(sorted(set(checkpoints)))
    escalates = bool(ACCEPTANCE_CHECKPOINTS.intersection(checkpoint_names))
    domains: list[ImpactDomain] = []
    skipped: list[SkippedGate] = []
    local_domains: list[str] = []
    carried_domains: list[str] = []

    for record in plan.domains:
        evidence = carried.get((record.domain, record.fingerprint))
        if evidence:
            carried_domains.append(record.domain)
            skipped.append(SkippedGate("local-domain", "unchanged-green-evidence-carried-forward", record.domain))
            domains.append(
                ImpactDomain(
                    record.domain,
                    record.fingerprint,
                    "carry-forward",
                    "source, commands, toolchain, inputs, and changed material match prior green evidence",
                    record.runner,
                    record.toolchain,
                    evidence,
                )
            )
        else:
            local_domains.append(record.domain)
            domains.append(
                ImpactDomain(
                    record.domain,
                    record.fingerprint,
                    "run",
                    "no matching green evidence is available for this fingerprint",
                    record.runner,
                    record.toolchain,
                )
            )

    for domain_id in sorted(config.domains):
        if domain_id not in selected:
            skipped.append(SkippedGate("local-domain", "unchanged-domain-not-selected-by-impact-plan", domain_id))

    if plan.state == "superseded":
        skipped.append(SkippedGate("local-ci", "superseded-candidate-range"))
        github_ci = "skip"
        github_reason = "candidate range is superseded; retry on a current base/head pair"
    elif escalates:
        github_ci = "required"
        github_reason = "named acceptance checkpoint requires hosted or integration proof after minimum local evidence"
    else:
        skipped.append(SkippedGate("github-ci", "no-named-acceptance-checkpoint"))
        github_ci = "skip"
        github_reason = (
            "minimum local proof is sufficient until shared-contract, merge, release, deployment, "
            "or live-proof checkpoint"
        )

    update_protocol = {
        "reportProgress": True,
        "carryForwardUnchangedGreenEvidence": True,
        "selectMinimumProof": True,
        "recordSkippedGates": True,
        "avoidRedundantLocalAndGithubCi": True,
        "escalateOnlyAtNamedAcceptanceCheckpoints": sorted(ACCEPTANCE_CHECKPOINTS),
    }
    return ImpactContract(
        1,
        plan.state,
        plan.base,
        plan.head,
        checkpoint_names,
        "named-acceptance-checkpoint" if escalates else "none",
        tuple(domains),
        tuple(skipped),
        tuple(sorted(local_domains)),
        tuple(sorted(carried_domains)),
        github_ci,
        github_reason,
        update_protocol,
    )


def _load_carried_evidence(evidence_dir: Path | None) -> dict[tuple[str, str], CarriedEvidence]:
    if evidence_dir is None or not evidence_dir.exists():
        return {}
    carried: dict[tuple[str, str], CarriedEvidence] = {}
    for path in sorted(evidence_dir.rglob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not _is_green_evidence(item):
            continue
        domain = item["domain"]
        fingerprint = item["fingerprint"]
        evidence = CarriedEvidence(
            domain,
            fingerprint,
            hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            str(item.get("base", "")),
            str(item.get("head", "")),
            int(item.get("runId", 0)),
        )
        carried[(domain, fingerprint)] = evidence
    return carried


def _is_green_evidence(item: Any) -> bool:
    return (
        isinstance(item, dict)
        and item.get("schemaVersion") == 1
        and isinstance(item.get("domain"), str)
        and isinstance(item.get("fingerprint"), str)
        and item.get("result") == "pass"
    )
