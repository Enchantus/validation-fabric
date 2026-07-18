"""Tests for configuration parsing and validation."""

import json
from pathlib import Path
import tempfile

import pytest
import yaml

from validation_fabric.config import Config, Domain


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink()


def test_domain_creation():
    """Test Domain dataclass creation."""
    domain = Domain(name="test", description="Test domain", required_checks=["lint"])
    assert domain.name == "test"
    assert domain.description == "Test domain"
    assert domain.required_checks == ["lint"]


def test_domain_to_dict():
    """Test Domain serialization to dict."""
    domain = Domain(name="test", description="Test", required_checks=["a", "b"])
    d = domain.to_dict()
    assert d["name"] == "test"
    assert d["description"] == "Test"
    assert d["required_checks"] == ["a", "b"]


def test_config_from_yaml_basic(temp_yaml_file):
    """Test basic YAML configuration parsing."""
    config_data = {
        "version": "1.0",
        "domains": {
            "default": {
                "description": "Default domain",
                "required_checks": ["lint", "test"],
            }
        },
        "transitive_requirements": {},
    }
    with open(temp_yaml_file, "w") as f:
        yaml.dump(config_data, f)

    config = Config.from_yaml(temp_yaml_file)
    assert config.version == "1.0"
    assert "default" in config.domains
    assert config.domains["default"].required_checks == ["lint", "test"]


def test_config_from_yaml_with_transitive(temp_yaml_file):
    """Test YAML with transitive requirements."""
    config_data = {
        "version": "1.0",
        "domains": {
            "backend": {"required_checks": ["test"]},
            "frontend": {"required_checks": ["lint"]},
        },
        "transitive_requirements": {
            "backend": ["frontend"],
        },
    }
    with open(temp_yaml_file, "w") as f:
        yaml.dump(config_data, f)

    config = Config.from_yaml(temp_yaml_file)
    assert config.get_transitive_requirements("backend") == ["frontend"]
    assert config.get_transitive_requirements("frontend") == []


def test_config_from_yaml_missing_file():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        Config.from_yaml("nonexistent.yml")


def test_config_from_yaml_invalid_version(temp_yaml_file):
    """Test that invalid version format raises ValueError."""
    config_data = {"version": 123, "domains": {}}
    with open(temp_yaml_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ValueError, match="Invalid version format"):
        Config.from_yaml(temp_yaml_file)


def test_config_from_yaml_invalid_domains(temp_yaml_file):
    """Test that invalid domains format raises ValueError."""
    config_data = {"version": "1.0", "domains": "not a dict"}
    with open(temp_yaml_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ValueError, match="domains must be a dictionary"):
        Config.from_yaml(temp_yaml_file)


def test_config_from_yaml_invalid_domain_spec(temp_yaml_file):
    """Test that invalid domain spec raises ValueError."""
    config_data = {"version": "1.0", "domains": {"bad": "not a dict"}}
    with open(temp_yaml_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ValueError, match="Invalid domain specification"):
        Config.from_yaml(temp_yaml_file)


def test_config_to_json():
    """Test configuration serialization to JSON."""
    config = Config(
        version="1.0",
        domains={
            "test": Domain(name="test", description="Test", required_checks=["a"])
        },
        transitive_requirements={"test": ["other"]},
    )

    json_str = config.to_json()
    data = json.loads(json_str)

    assert data["schema_version"] == "1.0"
    assert "test" in data["domains"]
    assert data["domains"]["test"]["name"] == "test"
    assert data["transitive_requirements"]["test"] == ["other"]


def test_config_fingerprint():
    """Test deterministic fingerprint generation."""
    config = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["check"])},
    )

    fp1 = config.fingerprint()
    fp2 = config.fingerprint()

    assert fp1 == fp2
    assert len(fp1) == 64


def test_config_fingerprint_differs_on_change():
    """Test that fingerprint changes when config changes."""
    config1 = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["a"])},
    )
    config2 = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["a", "b"])},
    )

    assert config1.fingerprint() != config2.fingerprint()


def test_config_select_domains_all():
    """Test domain selection returns all when none specified."""
    config = Config(
        version="1.0",
        domains={
            "a": Domain(name="a", required_checks=["check"]),
            "b": Domain(name="b", required_checks=["check"]),
        },
    )

    selected = config.select_domains(None)
    assert len(selected) == 2
    assert "a" in selected
    assert "b" in selected


def test_config_select_domains_specific():
    """Test selecting specific domains."""
    config = Config(
        version="1.0",
        domains={
            "a": Domain(name="a", required_checks=["check"]),
            "b": Domain(name="b", required_checks=["check"]),
        },
    )

    selected = config.select_domains(["a"])
    assert len(selected) == 1
    assert "a" in selected
    assert "b" not in selected


def test_config_select_domains_unknown():
    """Test that selecting unknown domain raises ValueError."""
    config = Config(version="1.0", domains={})

    with pytest.raises(ValueError, match="Unknown domain"):
        config.select_domains(["unknown"])


def test_config_empty_domains():
    """Test configuration with no domains."""
    config = Config(version="1.0", domains={})
    assert len(config.domains) == 0
    assert config.to_json() is not None
