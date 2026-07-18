from validation_fabric.github import RunIdentity, verify_run_identity


class Api:
    def __init__(self, run, pull):
        self.run = run
        self.pull = pull

    def get(self, path):
        return self.run if path.startswith("actions/") else self.pull


def identity():
    return RunIdentity("o/r", 7, "Validation Fabric", "pull_request", "success", "base", "head", 12)


def test_privileged_plane_rechecks_every_identity_field():
    run = {
        "name": "Validation Fabric",
        "event": "pull_request",
        "conclusion": "success",
        "head_sha": "head",
        "pull_requests": [{"number": 12}],
    }
    pull = {"base": {"sha": "base"}, "head": {"sha": "head"}}
    assert verify_run_identity(Api(run, pull), identity())["verified"] is True
    run["head_sha"] = "attacker"
    result = verify_run_identity(Api(run, pull), identity())
    assert result["verified"] is False
    assert "head-mismatch" in result["failures"]


def test_moved_pr_head_is_rejected():
    run = {
        "name": "Validation Fabric",
        "event": "pull_request",
        "conclusion": "success",
        "head_sha": "head",
        "pull_requests": [{"number": 12}],
    }
    pull = {"base": {"sha": "base"}, "head": {"sha": "new"}}
    assert "current-head-mismatch" in verify_run_identity(Api(run, pull), identity())["failures"]
