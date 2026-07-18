import subprocess
from pathlib import Path

from validation_fabric.config import load_config
from validation_fabric.core import build_plan, select_domains

CONFIG = """schemaVersion: 1
defaultBranch: main
fallbackDomains: [validation]
domains:
  - id: validation
    paths: [\"tools/**\"]
    inputs: [\".validation-fabric.yml\"]
    commands: [[\"python\", \"-c\", \"print('ok')\"]]
  - id: app
    paths: [\"src/**\"]
    inputs: [\"pyproject.toml\"]
    commands: [[\"python\", \"-c\", \"print('ok')\"]]
    requires: [validation]
"""


def test_selection_closes_requirements_and_falls_back(tmp_path: Path):
    path = tmp_path / ".validation-fabric.yml"
    path.write_text(CONFIG, encoding="utf-8")
    config = load_config(path)
    assert select_domains(["src/a.py"], config) == (["app", "validation"], [])
    assert select_domains(["new.unknown"], config) == (["validation"], ["new.unknown"])


def test_plan_is_deterministic_and_exact(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    (tmp_path / ".validation-fabric.yml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "head"], cwd=tmp_path, check=True, capture_output=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    config = load_config(tmp_path / ".validation-fabric.yml")
    first = build_plan(tmp_path, config, base, head)
    second = build_plan(tmp_path, config, base, head)
    assert first == second
    assert [item.domain for item in first.domains] == ["app", "validation"]


def test_missing_pinned_range_is_neutral_supersession(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".validation-fabric.yml").write_text(CONFIG, encoding="utf-8")
    config = load_config(tmp_path / ".validation-fabric.yml")
    plan = build_plan(tmp_path, config, "0" * 40, "1" * 40)
    assert plan.state == "superseded"


def test_deleted_owned_file_remains_in_exact_plan(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    (tmp_path / ".validation-fabric.yml").write_text(CONFIG, encoding="utf-8")
    source = tmp_path / "src" / "removed.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    source.unlink()
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "delete"], cwd=tmp_path, check=True, capture_output=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    plan = build_plan(tmp_path, load_config(tmp_path / ".validation-fabric.yml"), base, head)
    assert plan.changed == ("src/removed.py",)
    assert [item.domain for item in plan.domains] == ["app", "validation"]
