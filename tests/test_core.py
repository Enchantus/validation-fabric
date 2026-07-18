"""Tests for core validation logic."""

import pytest

from validation_fabric.config import Config, Domain
from validation_fabric.core import ValidationResult, RequirementResolver, DomainPlan


def test_validation_result_creation():
    """Test ValidationResult creation."""
    result = ValidationResult(
        check_name="lint",
        domain="backend",
        passed=True,
        details="Linting passed",
    )
    assert result.check_name == "lint"
    assert result.domain == "backend"
    assert result.passed is True


def test_validation_result_to_dict():
    """Test ValidationResult serialization."""
    result = ValidationResult(
        check_name="test", domain="frontend", passed=False, details="Error"
    )
    d = result.to_dict()
    assert d["check_name"] == "test"
    assert d["domain"] == "frontend"
    assert d["passed"] is False
    assert d["details"] == "Error"


def test_domain_plan_to_dict():
    """Test DomainPlan serialization."""
    plan = DomainPlan(
        domain_name="test",
        required_checks=["a", "b"],
        transitive_requirements=["c"],
        fingerprint="abc123",
    )
    d = plan.to_dict()
    assert d["domain_name"] == "test"
    assert d["required_checks"] == ["a", "b"]
    assert d["transitive_requirements"] == ["c"]
    assert d["fingerprint"] == "abc123"


def test_requirement_resolver_basic():
    """Test basic requirement resolution."""
    config = Config(
        version="1.0",
        domains={
            "backend": Domain(name="backend", required_checks=["test"]),
            "frontend": Domain(name="frontend", required_checks=["lint"]),
        },
        transitive_requirements={"backend": ["frontend"]},
    )

    resolver = RequirementResolver(config)
    requirements = resolver.resolve_all_requirements("backend")

    assert "frontend" in requirements


def test_requirement_resolver_no_requirements():
    """Test resolution with no transitive requirements."""
    config = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["check"])},
        transitive_requirements={},
    )

    resolver = RequirementResolver(config)
    requirements = resolver.resolve_all_requirements("test")

    assert len(requirements) == 0


def test_requirement_resolver_transitive_chain():
    """Test resolution of chained transitive requirements."""
    config = Config(
        version="1.0",
        domains={
            "a": Domain(name="a", required_checks=["check"]),
            "b": Domain(name="b", required_checks=["check"]),
            "c": Domain(name="c", required_checks=["check"]),
        },
        transitive_requirements={
            "a": ["b"],
            "b": ["c"],
        },
    )

    resolver = RequirementResolver(config)
    requirements = resolver.resolve_all_requirements("a")

    assert "b" in requirements
    assert "c" in requirements


def test_requirement_resolver_diamond_dependency():
    """Test resolution with diamond dependency."""
    config = Config(
        version="1.0",
        domains={
            "a": Domain(name="a", required_checks=["check"]),
            "b": Domain(name="b", required_checks=["check"]),
            "c": Domain(name="c", required_checks=["check"]),
            "d": Domain(name="d", required_checks=["check"]),
        },
        transitive_requirements={
            "a": ["b", "c"],
            "b": ["d"],
            "c": ["d"],
        },
    )

    resolver = RequirementResolver(config)
    requirements = resolver.resolve_all_requirements("a")

    assert requirements == {"b", "c", "d"}


def test_requirement_resolver_caching():
    """Test that requirement resolution is cached."""
    config = Config(
        version="1.0",
        domains={
            "a": Domain(name="a", required_checks=["check"]),
            "b": Domain(name="b", required_checks=["check"]),
        },
        transitive_requirements={"a": ["b"]},
    )

    resolver = RequirementResolver(config)
    req1 = resolver.resolve_all_requirements("a")
    req2 = resolver.resolve_all_requirements("a")

    assert req1 is req2


def test_requirement_resolver_create_plan():
    """Test plan creation."""
    config = Config(
        version="1.0",
        domains={
            "backend": Domain(name="backend", required_checks=["test", "lint"]),
            "frontend": Domain(name="frontend", required_checks=["lint"]),
        },
        transitive_requirements={"backend": ["frontend"]},
    )

    resolver = RequirementResolver(config)
    plan = resolver.create_plan("backend")

    assert plan.domain_name == "backend"
    assert set(plan.required_checks) == {"test", "lint"}
    assert "frontend" in plan.transitive_requirements
    assert len(plan.fingerprint) == 64


def test_requirement_resolver_create_plan_unknown_domain():
    """Test that planning for unknown domain raises ValueError."""
    config = Config(version="1.0", domains={})
    resolver = RequirementResolver(config)

    with pytest.raises(ValueError, match="Unknown domain"):
        resolver.create_plan("unknown")


def test_requirement_resolver_plan_fingerprint_deterministic():
    """Test that plan fingerprints are deterministic."""
    config = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["a"])},
    )

    resolver = RequirementResolver(config)
    plan1 = resolver.create_plan("test")
    plan2 = resolver.create_plan("test")

    assert plan1.fingerprint == plan2.fingerprint


def test_requirement_resolver_plan_fingerprint_changes():
    """Test that fingerprint changes when plan changes."""
    config1 = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["a"])},
    )
    config2 = Config(
        version="1.0",
        domains={"test": Domain(name="test", required_checks=["a", "b"])},
    )

    resolver1 = RequirementResolver(config1)
    resolver2 = RequirementResolver(config2)

    plan1 = resolver1.create_plan("test")
    plan2 = resolver2.create_plan("test")

    assert plan1.fingerprint != plan2.fingerprint
