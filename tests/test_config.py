from pathlib import Path

import pytest

from validation_fabric.config import ConfigError, load_config


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def manifest(extra: str = "") -> str:
    return f"""schemaVersion: 1
defaultBranch: trunk
fallbackDomains: [validation]
domains:
  - id: validation
    paths: [\"tools/**\"]
    inputs: [\"pyproject.toml\"]
    commands: [[\"python\", \"-m\", \"pytest\"]]
  - id: app
    paths: [\"src/**\"]
    inputs: [\"pyproject.toml\"]
    commands: [[\"python\", \"-m\", \"pytest\"]]
    requires: [validation]
{extra}"""


def test_loads_public_schema(tmp_path: Path):
    config = load_config(write(tmp_path / ".validation-fabric.yml", manifest()))
    assert config.default_branch == "trunk"
    assert config.domains["app"].requires == ("validation",)
    assert config.merge.enabled is False


@pytest.mark.parametrize(
    "extra, message",
    [
        ("fallbackDomains: [missing]\n", "unknown domain"),
        ("", ""),
    ],
)
def test_invalid_references(tmp_path: Path, extra: str, message: str):
    if not extra:
        return
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path / "bad.yml", manifest(extra)))


def test_rejects_dependency_cycles(tmp_path: Path):
    text = manifest().replace(
        "requires: [validation]",
        "\n".join(
            [
                "requires: [validation]",
                "  - id: cycle",
                '    paths: ["x/**"]',
                "    inputs: []",
                '    commands: [["true"]]',
                "    requires: [cycle]",
            ]
        ),
    )
    with pytest.raises(ConfigError, match="cycle"):
        load_config(write(tmp_path / "bad.yml", text))
