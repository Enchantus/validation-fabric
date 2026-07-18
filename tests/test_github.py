from validation_fabric.github import RunIdentity, verify_run_identity


class Api:
    def __init__(self, run, pull):
        self.run = run
        self.pull = pull

    def get(self, path):
        return self.run if path.startswith("actions/") else self.pull


def identity():
    return RunIdentity(
        "o/r",
        7,
        "Validation Fabric",
        "pull_request_target",
        "success",
        "base",
        "head",
        12,
        ".github/workflows/validation-fabric.yml",
        "fork/r",
        "Validation Fabric PR #12 @ head",
    )


def test_privileged_plane_rechecks_every_identity_field():
    run = {
        "name": "Validation Fabric",
        "event": "pull_request_target",
        "conclusion": "success",
        "head_sha": "base",
        "display_title": "Validation Fabric PR #12 @ head",
        "path": ".github/workflows/validation-fabric.yml",
        "repository": {"full_name": "o/r"},
        "head_repository": {"full_name": "fork/r"},
    }
    pull = {
        "base": {"sha": "base", "repo": {"full_name": "o/r"}},
        "head": {"sha": "head", "repo": {"full_name": "fork/r"}},
    }
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
        "head_sha": "base",
        "display_title": "Validation Fabric PR #12 @ head",
        "path": ".github/workflows/validation-fabric.yml",
        "repository": {"full_name": "o/r"},
        "head_repository": {"full_name": "fork/r"},
    }
    pull = {
        "base": {"sha": "base", "repo": {"full_name": "o/r"}},
        "head": {"sha": "new", "repo": {"full_name": "fork/r"}},
    }
    assert "current-head-mismatch" in verify_run_identity(Api(run, pull), identity())["failures"]
