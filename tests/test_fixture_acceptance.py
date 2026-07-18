import subprocess
from pathlib import Path

import pytest

from validation_fabric.config import load_config
from validation_fabric.core import build_plan, select_domains

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("preset", "changed", "expected"),
    [
        ("python", ["src/app.py"], ["python"]),
        ("node", ["src/app.ts"], ["node"]),
        ("go", ["cmd/app/main.go"], ["go"]),
        ("polyglot", ["backend/app.py", "web/app.ts", "edge/main.go"], ["go", "python", "web"]),
    ],
)
def test_language_examples_select_expected_domains(preset: str, changed: list[str], expected: list[str]) -> None:
    config = load_config(ROOT / "examples" / preset / ".validation-fabric.yml")
    selected, unknown = select_domains(changed, config)
    assert selected == expected
    assert unknown == []


def test_polyglot_example_proves_non_main_default_branch() -> None:
    config = load_config(ROOT / "examples" / "polyglot" / ".validation-fabric.yml")
    assert config.default_branch == "trunk"


@pytest.mark.parametrize("preset", ["python", "node", "go", "polyglot"])
def test_language_examples_are_complete_fixture_repositories(preset: str) -> None:
    root = ROOT / "examples" / preset
    expected = {
        "python": ["pyproject.toml", "src/fixture.py", "tests/test_fixture.py"],
        "node": ["package.json", "package-lock.json", "src/add.js", "test/add.test.js"],
        "go": ["go.mod", "add.go", "add_test.go"],
        "polyglot": [
            "backend/app.py",
            "backend/tests/test_app.py",
            "web/package.json",
            "web/package-lock.json",
            "edge/go.mod",
            "edge/add.go",
        ],
    }
    assert all((root / relative).is_file() for relative in expected[preset])


def test_docs_only_and_unknown_paths_are_conservative(tmp_path: Path) -> None:
    manifest = tmp_path / ".validation-fabric.yml"
    manifest.write_text(
        """schemaVersion: 1
defaultBranch: main
fallbackDomains: [code]
domains:
  - id: docs
    paths: ["docs/**", "README.md"]
    inputs: ["docs/**"]
    commands: [["python", "-c", "print('docs')"]]
  - id: code
    paths: ["src/**"]
    inputs: ["src/**"]
    commands: [["python", "-c", "print('code')"]]
""",
        encoding="utf-8",
    )
    config = load_config(manifest)
    assert select_domains(["docs/guide.md"], config) == (["docs"], [])
    assert select_domains(["new-root-file"], config) == (["code"], ["new-root-file"])


def test_rename_and_empty_ranges_are_exact(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    (tmp_path / ".validation-fabric.yml").write_text(
        """schemaVersion: 1
defaultBranch: main
fallbackDomains: [code]
domains:
  - id: code
    paths: ["src/**"]
    inputs: ["src/**"]
    commands: [["python", "-c", "print('ok')"]]
""",
        encoding="utf-8",
    )
    source = tmp_path / "src" / "before.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    source.rename(source.with_name("after.py"))
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "rename"], cwd=tmp_path, check=True, capture_output=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    config = load_config(tmp_path / ".validation-fabric.yml")
    renamed = build_plan(tmp_path, config, base, head)
    empty = build_plan(tmp_path, config, head, head)
    assert renamed.changed == ("src/after.py",)
    assert [item.domain for item in renamed.domains] == ["code"]
    assert empty.changed == ()
    assert empty.domains == ()
