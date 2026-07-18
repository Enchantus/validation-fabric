"""Tests for evidence and certificate generation."""

import json

import pytest

from validation_fabric.core import ValidationResult
from validation_fabric.certificates import Evidence, Certificate


def test_evidence_from_result():
    """Test Evidence creation from ValidationResult."""
    result = ValidationResult(
        check_name="lint", domain="backend", passed=True, details="OK"
    )
    evidence = Evidence.from_result(result, timestamp="2026-01-01T00:00:00")

    assert evidence.check_name == "lint"
    assert evidence.domain == "backend"
    assert evidence.passed is True
    assert evidence.details == "OK"
    assert evidence.timestamp == "2026-01-01T00:00:00"


def test_evidence_auto_timestamp():
    """Test that Evidence auto-generates timestamp when not provided."""
    result = ValidationResult(
        check_name="test", domain="app", passed=True, details=""
    )
    evidence = Evidence.from_result(result)

    assert evidence.timestamp is not None
    assert "T" in evidence.timestamp


def test_evidence_to_dict():
    """Test Evidence serialization."""
    evidence = Evidence(
        check_name="test",
        domain="backend",
        timestamp="2026-01-01T00:00:00",
        passed=True,
        details="Passed",
    )
    d = evidence.to_dict()

    assert d["check_name"] == "test"
    assert d["domain"] == "backend"
    assert d["timestamp"] == "2026-01-01T00:00:00"
    assert d["passed"] is True
    assert d["details"] == "Passed"


def test_certificate_creation():
    """Test Certificate creation."""
    cert = Certificate(
        domain="backend",
        admitted=True,
        config_fingerprint="abc123",
        issued_at="2026-01-01T00:00:00",
    )

    assert cert.domain == "backend"
    assert cert.admitted is True
    assert cert.config_fingerprint == "abc123"
    assert cert.certificate_id is not None


def test_certificate_auto_fields():
    """Test that Certificate auto-generates issued_at and certificate_id."""
    cert = Certificate(domain="test", admitted=True, config_fingerprint="fp123")

    assert cert.issued_at is not None
    assert cert.certificate_id is not None
    assert len(cert.certificate_id) == 16


def test_certificate_add_evidence():
    """Test adding evidence to a certificate."""
    cert = Certificate(domain="test", admitted=True, config_fingerprint="fp")

    evidence = Evidence(
        check_name="lint",
        domain="test",
        timestamp="2026-01-01T00:00:00",
        passed=True,
    )
    cert.add_evidence(evidence)

    assert len(cert.evidence) == 1
    assert cert.evidence[0].check_name == "lint"


def test_certificate_id_deterministic():
    """Test that certificate IDs are deterministic for same data."""
    cert1 = Certificate(
        domain="test",
        admitted=True,
        config_fingerprint="fp",
        issued_at="2026-01-01T00:00:00",
    )
    cert2 = Certificate(
        domain="test",
        admitted=True,
        config_fingerprint="fp",
        issued_at="2026-01-01T00:00:00",
    )

    assert cert1.certificate_id == cert2.certificate_id


def test_certificate_id_changes_on_evidence():
    """Test that certificate ID changes when evidence is added."""
    cert = Certificate(
        domain="test",
        admitted=True,
        config_fingerprint="fp",
        issued_at="2026-01-01T00:00:00",
    )
    old_id = cert.certificate_id

    evidence = Evidence(
        check_name="check",
        domain="test",
        timestamp="2026-01-01T00:00:00",
        passed=True,
    )
    cert.add_evidence(evidence)

    assert cert.certificate_id != old_id


def test_certificate_to_dict():
    """Test Certificate serialization to dict."""
    cert = Certificate(
        domain="backend",
        admitted=True,
        config_fingerprint="fp123",
        issued_at="2026-01-01T00:00:00",
    )

    d = cert.to_dict()

    assert d["domain"] == "backend"
    assert d["admitted"] is True
    assert d["config_fingerprint"] == "fp123"
    assert d["issued_at"] == "2026-01-01T00:00:00"
    assert "certificate_id" in d
    assert isinstance(d["evidence"], list)


def test_certificate_to_json():
    """Test Certificate serialization to JSON."""
    cert = Certificate(
        domain="test", admitted=True, config_fingerprint="fp", issued_at="2026-01-01T00:00:00"
    )

    json_str = cert.to_json()
    data = json.loads(json_str)

    assert data["schema_version"] == "1.0"
    assert "certificate" in data
    assert data["certificate"]["domain"] == "test"


def test_certificate_json_with_evidence():
    """Test Certificate JSON includes evidence."""
    cert = Certificate(
        domain="test",
        admitted=True,
        config_fingerprint="fp",
        issued_at="2026-01-01T00:00:00",
    )

    evidence = Evidence(
        check_name="test",
        domain="test",
        timestamp="2026-01-01T00:00:00",
        passed=True,
    )
    cert.add_evidence(evidence)

    json_str = cert.to_json()
    data = json.loads(json_str)

    assert len(data["certificate"]["evidence"]) == 1
    assert data["certificate"]["evidence"][0]["check_name"] == "test"


def test_certificate_admission_false():
    """Test creating a denied certificate."""
    cert = Certificate(
        domain="test",
        admitted=False,
        config_fingerprint="fp",
        issued_at="2026-01-01T00:00:00",
    )

    assert cert.admitted is False
    d = cert.to_dict()
    assert d["admitted"] is False
