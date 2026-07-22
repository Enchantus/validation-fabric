import json
import subprocess
from pathlib import Path

from validation_fabric.cli import main
from validation_fabric.config import load_config
from validation_fabric.core import build_plan
from validation_fabric.impact import build_impact_contract

CONFIG = """schemaVersion: 1
defaultBranch: main
fallbackDomains: [validation]
domains:
  - id: validation
    paths: ["tools/**"]
    inputs: [".validation-fabric.yml"]
    commands: [["python", "-m", "pytest", "tests/test_policy.py"]]
    toolchain: {python: "3.11"}
  - id: app
    paths: ["src/**"]
    inputs: ["pyproject.toml", "src/**"]
    commands: [["python", "-m", "pytest", "tests/test_app.py"]]
    toolchain: {python: "3.11"}
    requires: [validation]
  - id: docs
    paths: ["docs/**"]
    inputs: ["docs/**"]
    commands: [["python", "-c", "print('docs')"]]
"""


def commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def initialized_repo(tmp_path: Path) -> tuple[Path, str, str]:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    (tmp_path / ".validation-fabric.yml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")
    base = commit(tmp_path, "base")
    (tmp_path / "src" / "app.py").write_text("value = 2\n", encoding="utf-8")
    head = commit(tmp_path, "head")
    return tmp_path, base, head


def test_impact_contract_selects_minimum_proof_and_records_skipped_gates(tmp_path: Path) -> None:
    root, base, head = initialized_repo(tmp_path)
    config = load_config(root / ".validation-fabric.yml")
    plan = build_plan(root, config, base, head)

    contract = build_impact_contract(plan, config).to_dict()

    assert contract["localDomains"] == ["app", "validation"]
    assert contract["carriedDomains"] == []
    assert contract["githubCi"] == "skip"
    skipped_docs = {"gate": "local-domain", "reason": "unchanged-domain-not-selected-by-impact-plan", "domain": "docs"}
    assert skipped_docs in contract["skippedGates"]
    assert {"gate": "github-ci", "reason": "no-named-acceptance-checkpoint", "domain": ""} in contract[
        "skippedGates"
    ]


def test_impact_contract_carries_matching_green_evidence(tmp_path: Path) -> None:
    root, base, head = initialized_repo(tmp_path)
    config = load_config(root / ".validation-fabric.yml")
    plan = build_plan(root, config, base, head)
    evidence_dir = root / ".validation-fabric" / "evidence"
    evidence_dir.mkdir(parents=True)
    app = next(record for record in plan.domains if record.domain == "app")
    (evidence_dir / "app.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "repository": "local",
                "runId": 123,
                "base": "older-base",
                "head": "older-head",
                "domain": "app",
                "fingerprint": app.fingerprint,
                "result": "pass",
                "commands": [],
            }
        ),
        encoding="utf-8",
    )

    contract = build_impact_contract(plan, config, evidence_dir).to_dict()

    assert contract["localDomains"] == ["validation"]
    assert contract["carriedDomains"] == ["app"]
    assert contract["domains"][0]["decision"] == "carry-forward"
    assert contract["domains"][0]["carriedEvidence"]["sourceRunId"] == 123
    assert {"gate": "local-domain", "reason": "unchanged-green-evidence-carried-forward", "domain": "app"} in contract[
        "skippedGates"
    ]


def test_impact_contract_escalates_only_at_named_acceptance_checkpoints(tmp_path: Path) -> None:
    root, base, head = initialized_repo(tmp_path)
    config = load_config(root / ".validation-fabric.yml")
    plan = build_plan(root, config, base, head)

    contract = build_impact_contract(plan, config, checkpoints=("merge",)).to_dict()

    assert contract["githubCi"] == "required"
    assert contract["escalation"] == "named-acceptance-checkpoint"
    assert contract["acceptanceCheckpoints"] == ["merge"]


def test_cli_impact_emits_update_contract(tmp_path: Path, capsys) -> None:
    root, base, head = initialized_repo(tmp_path)

    assert main(["--repo-root", str(root), "impact", "--base", base, "--head", head]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["schemaVersion"] == 1
    assert output["updateProtocol"]["selectMinimumProof"] is True
    assert output["localDomains"] == ["app", "validation"]
