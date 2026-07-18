import json
from pathlib import Path

from validation_fabric.cli import main
from validation_fabric.config import load_config


def test_init_and_doctor_emit_versioned_json(tmp_path: Path, capsys):
    assert main(["--repo-root", str(tmp_path), "init", "--preset", "python"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["schemaVersion"] == 1
    assert (tmp_path / ".validation-fabric.yml").is_file()
    assert main(["--repo-root", str(tmp_path), "doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_init_presets_create_the_documented_domain_shapes(tmp_path: Path, capsys) -> None:
    expected = {
        "python": ["python"],
        "node": ["node"],
        "go": ["go"],
        "polyglot": ["go", "python", "web"],
    }
    for preset, domains in expected.items():
        root = tmp_path / preset
        root.mkdir()
        assert main(["--repo-root", str(root), "init", "--preset", preset]) == 0
        capsys.readouterr()
        config = load_config(root / ".validation-fabric.yml")
        assert sorted(config.domains) == domains
        assert config.merge.enabled is False


def test_doctor_reports_errors_without_exiting(tmp_path: Path, capsys):
    assert main(["--repo-root", str(tmp_path), "doctor"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False


def test_event_and_status_emit_versioned_json_without_a_manifest(tmp_path: Path, capsys) -> None:
    common = ["--repo-root", str(tmp_path)]
    assert (
        main(
            [
                *common,
                "event",
                "candidate.created",
                "--event-id",
                "run-1-created",
                "--candidate",
                "head",
                "--occurred-at",
                "2026-01-01T00:00:00Z",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "appended"
    assert (
        main(
            [
                *common,
                "status",
                "--event-dir",
                ".validation-fabric/events",
                "--candidate",
                "head",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "created"
