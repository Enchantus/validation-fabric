from validation_fabric.certificates import admit, issue_certificate, verify_certificate


def test_certificate_signatures_fail_closed():
    envelope = issue_certificate({"admitted": True, "head": "abc"}, "key")
    assert verify_certificate(envelope, "key")
    envelope["certificate"]["head"] = "other"
    assert not verify_certificate(envelope, "key")


def test_admission_binds_repository_run_and_exact_candidate():
    plan = {"state": "planned", "base": "base", "head": "head", "domains": [{"domain": "app", "fingerprint": "fp"}]}
    evidence = [
        {
            "schemaVersion": 1,
            "repository": "o/r",
            "runId": 7,
            "base": "base",
            "head": "head",
            "domain": "app",
            "fingerprint": "fp",
            "result": "pass",
            "commands": [],
        }
    ]
    envelope = admit(plan, evidence, "o/r", 7, "key")
    assert envelope["certificate"]["admitted"] is True
    evidence[0]["runId"] = 8
    rejected = admit(plan, evidence, "o/r", 7, "key")
    assert rejected["certificate"]["admitted"] is False


def test_unsigned_or_wrong_candidate_evidence_cannot_admit():
    plan = {"state": "planned", "base": "base", "head": "head", "domains": [{"domain": "app", "fingerprint": "fp"}]}
    evidence = [
        {
            "schemaVersion": 1,
            "repository": "o/r",
            "runId": 7,
            "base": "base",
            "head": "attacker",
            "domain": "app",
            "fingerprint": "fp",
            "result": "pass",
            "commands": [],
        }
    ]
    assert admit(plan, evidence, "o/r", 7, "key")["certificate"]["admitted"] is False
