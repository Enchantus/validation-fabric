from validation_fabric.config import FabricConfig, MergeConfig
from validation_fabric.merge import decide_merge, result_exit_code


class Api:
    def __init__(self):
        self.pull = {
            "state": "open",
            "head": {"sha": "head"},
            "base": {"sha": "base"},
            "mergeable": True,
            "mergeable_state": "clean",
        }
        self.posts = []
        self.checks = [
            {
                "name": "Validation Fabric / admission",
                "head_sha": "head",
                "status": "completed",
                "conclusion": "success",
            }
        ]

    def get(self, path):
        if path.startswith("git/ref"):
            return {"object": {"sha": "base"}}
        if path.startswith("commits/"):
            return {"check_runs": self.checks}
        return self.pull

    def put(self, path, payload):
        return {"merged": True, "sha": "merge"}

    def post(self, path, payload):
        self.posts.append((path, payload))
        return {}


def config(enabled=False):
    return FabricConfig(
        1, "trunk", (), {}, MergeConfig(enabled, "squash", "Validation Fabric / admission", ("ci.yml",))
    )


def test_merge_is_off_by_default():
    assert decide_merge(Api(), config(), 1, "head")["reason"] == "merge-disabled"


def test_stale_candidates_are_neutral():
    api = Api()
    api.pull["head"]["sha"] = "new"
    result = decide_merge(api, config(True), 1, "head")
    assert result["action"] == "superseded"
    assert result_exit_code(result) == 0


def test_exact_head_merges_and_dispatches_configured_workflows():
    api = Api()
    result = decide_merge(api, config(True), 1, "head")
    assert result["action"] == "merged"
    assert api.posts == [("actions/workflows/ci.yml/dispatches", {"ref": "trunk"})]


def test_merge_rejects_without_exact_successful_admission_check():
    api = Api()
    api.checks = []
    result = decide_merge(api, config(True), 1, "head")
    assert result == {"action": "reject", "reason": "admission-check-missing", "pullRequest": 1}


def test_merge_supersedes_certificate_for_an_old_base():
    result = decide_merge(Api(), config(True), 1, "head", "old-base")
    assert result == {"action": "superseded", "reason": "certificate-base-mismatch", "pullRequest": 1}
