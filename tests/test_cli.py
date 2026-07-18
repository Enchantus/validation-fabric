import json
from pathlib import Path

from validation_fabric.cli import main


def test_init_and_doctor_emit_versioned_json(tmp_path: Path, capsys):
    assert main(["--repo-root", str(tmp_path), "init", "--preset", "python"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["schemaVersion"] == 1
    assert (tmp_path / ".validation-fabric.yml").is_file()
    assert main(["--repo-root", str(tmp_path), "doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_doctor_reports_errors_without_exiting(tmp_path: Path, capsys):
    assert main(["--repo-root", str(tmp_path), "doctor"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
