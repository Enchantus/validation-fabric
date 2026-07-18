"""Tests for command-line interface."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from validation_fabric.cli import CLI


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cli_with_config(temp_dir):
    """Create a CLI instance with a valid config file."""
    config_file = temp_dir / ".validation-fabric.yml"
    config_data = {
        "version": "1.0",
        "domains": {
            "backend": {
                "description": "Backend validation",
                "required_checks": ["test", "lint"],
            },
            "frontend": {
                "description": "Frontend validation",
                "required_checks": ["lint"],
            },
        },
        "transitive_requirements": {
            "backend": ["frontend"],
        },
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return CLI(config_path=str(config_file))


def test_cli_init_creates_file(temp_dir):
    """Test that init command creates a configuration file."""
    config_file = temp_dir / ".validation-fabric.yml"
    cli = CLI(config_path=str(config_file))

    result = cli.cmd_init()

    assert result == 0
    assert config_file.exists()
    assert "version" in config_file.read_text()


def test_cli_init_fails_if_exists(temp_dir, cli_with_config):
    """Test that init fails if config already exists."""
    result = cli_with_config.cmd_init()

    assert result == 1


def test_cli_doctor(cli_with_config, capsys):
    """Test that doctor command reports configuration health."""
    result = cli_with_config.cmd_doctor()

    assert result == 0
    captured = capsys.readouterr()
    assert "Configuration Health Check" in captured.out
    assert "Domains: 2" in captured.out


def test_cli_plan_all_domains(cli_with_config, capsys):
    """Test plan command for all domains."""
    result = cli_with_config.cmd_plan(None)

    assert result == 0
    captured = capsys.readouterr()
    assert "backend" in captured.out or "frontend" in captured.out


def test_cli_plan_specific_domain(cli_with_config, capsys):
    """Test plan command for specific domain."""
    result = cli_with_config.cmd_plan("backend")

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["domain_name"] == "backend"
    assert "frontend" in output["transitive_requirements"]


def test_cli_plan_unknown_domain(cli_with_config):
    """Test plan command with unknown domain."""
    result = cli_with_config.cmd_plan("unknown")

    assert result == 1


def test_cli_run(cli_with_config, capsys):
    """Test run command."""
    result = cli_with_config.cmd_run("backend")

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["certificate"]["domain"] == "backend"
    assert output["certificate"]["admitted"] is True


def test_cli_run_unknown_domain(cli_with_config):
    """Test run command with unknown domain."""
    result = cli_with_config.cmd_run("unknown")

    assert result == 1


def test_cli_status(cli_with_config, capsys):
    """Test status command."""
    result = cli_with_config.cmd_status(None)

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "config_fingerprint" in output
    assert "domains" in output


def test_cli_status_specific_domain(cli_with_config, capsys):
    """Test status command for specific domain."""
    result = cli_with_config.cmd_status("backend")

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "backend" in output["domains"]


def test_cli_explain(cli_with_config, capsys):
    """Test explain command."""
    result = cli_with_config.cmd_explain("backend")

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["domain"] == "backend"
    assert "direct_checks" in output
    assert "transitive_requirements" in output


def test_cli_explain_unknown_domain(cli_with_config):
    """Test explain command with unknown domain."""
    result = cli_with_config.cmd_explain("unknown")

    assert result == 1


def test_cli_admit(cli_with_config, capsys):
    """Test admit command."""
    result = cli_with_config.cmd_admit("backend")

    assert result == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["certificate"]["domain"] == "backend"
    assert output["certificate"]["admitted"] is True


def test_cli_admit_unknown_domain(cli_with_config):
    """Test admit command with unknown domain."""
    result = cli_with_config.cmd_admit("unknown")

    assert result == 1


def test_cli_config_missing_file(temp_dir):
    """Test that missing config file returns error."""
    cli = CLI(config_path=str(temp_dir / "missing.yml"))

    result = cli.cmd_doctor()

    assert result == 1


def test_cli_load_config_caching(cli_with_config):
    """Test that config is cached after first load."""
    config1 = cli_with_config.load_config()
    config2 = cli_with_config.load_config()

    assert config1 is config2


def test_cli_main_no_args(capsys):
    """Test main function with no arguments."""
    from validation_fabric.cli import main

    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "help" in captured.out.lower() or captured.out == ""
