"""Optional exact-candidate merge controller."""

from __future__ import annotations

from typing import Any

from .config import FabricConfig
from .github import GitHubApi


def decide_merge(api: GitHubApi, config: FabricConfig, pull_number: int, admitted_head: str) -> dict[str, Any]:
    if not config.merge.enabled:
        return {"action": "skip", "reason": "merge-disabled", "pullRequest": pull_number}
    pull = api.get(f"pulls/{pull_number}")
    if pull.get("state") != "open":
        return {"action": "skip", "reason": "pull-request-not-open", "pullRequest": pull_number}
    if pull.get("head", {}).get("sha") != admitted_head:
        return {"action": "superseded", "reason": "stale-head", "pullRequest": pull_number}
    default_head = api.get(f"git/ref/heads/{config.default_branch}").get("object", {}).get("sha")
    if pull.get("base", {}).get("sha") != default_head:
        return {"action": "superseded", "reason": "stale-base", "pullRequest": pull_number}
    if pull.get("mergeable") is not True or pull.get("mergeable_state") not in {"clean", "has_hooks"}:
        return {"action": "reject", "reason": "pull-request-not-mergeable", "pullRequest": pull_number}
    merged = api.put(f"pulls/{pull_number}/merge", {"sha": admitted_head, "merge_method": config.merge.method})
    if not merged.get("merged"):
        return {"action": "reject", "reason": "merge-api-rejected", "pullRequest": pull_number}
    dispatched: list[str] = []
    for workflow in config.merge.post_merge_workflows:
        api.post(f"actions/workflows/{workflow}/dispatches", {"ref": config.default_branch})
        dispatched.append(workflow)
    return {
        "action": "merged",
        "pullRequest": pull_number,
        "head": admitted_head,
        "mergeSha": merged.get("sha"),
        "dispatched": dispatched,
    }


def result_exit_code(result: dict[str, Any]) -> int:
    return 1 if result.get("action") == "reject" else 0
