"""Trusted GitHub workflow-run verification helpers."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class GitHubApi(Protocol):
    def get(self, path: str) -> Any: ...
    def put(self, path: str, payload: dict[str, Any]) -> Any: ...
    def post(self, path: str, payload: dict[str, Any]) -> Any: ...


@dataclass
class HttpGitHubApi:
    repository: str
    token: str
    api_url: str = "https://api.github.com"

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.api_url}/repos/{self.repository}/{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {path} failed ({error.code}): {detail}") from error

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PUT", path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("POST", path, payload)


@dataclass(frozen=True)
class RunIdentity:
    repository: str
    run_id: int
    workflow_name: str
    event: str
    conclusion: str
    base: str
    head: str
    pull_request: int
    workflow_path: str = ""
    head_repository: str = ""
    run_title: str = ""


def verify_run_identity(api: GitHubApi, expected: RunIdentity) -> dict[str, Any]:
    """Re-read an untrusted run through the privileged API plane."""
    run = api.get(f"actions/runs/{expected.run_id}")
    failures: list[str] = []
    if run.get("repository", {}).get("full_name") != expected.repository:
        failures.append("repository-mismatch")
    if run.get("name") != expected.workflow_name:
        failures.append("workflow-name-mismatch")
    if run.get("event") != expected.event:
        failures.append("event-mismatch")
    if run.get("conclusion") != expected.conclusion:
        failures.append("conclusion-mismatch")
    expected_run_sha = expected.base if expected.event == "pull_request_target" else expected.head
    if run.get("head_sha") != expected_run_sha:
        failures.append("head-mismatch")
    if expected.run_title and run.get("display_title") != expected.run_title:
        failures.append("run-title-mismatch")
    if expected.workflow_path and run.get("path") != expected.workflow_path:
        failures.append("workflow-path-mismatch")
    if expected.head_repository and run.get("head_repository", {}).get("full_name") != expected.head_repository:
        failures.append("head-repository-mismatch")
    pull = api.get(f"pulls/{expected.pull_request}")
    if pull.get("base", {}).get("repo", {}).get("full_name") != expected.repository:
        failures.append("pull-repository-mismatch")
    if pull.get("base", {}).get("sha") != expected.base:
        failures.append("base-mismatch")
    if pull.get("head", {}).get("sha") != expected.head:
        failures.append("current-head-mismatch")
    if expected.head_repository and pull.get("head", {}).get("repo", {}).get("full_name") != expected.head_repository:
        failures.append("pull-head-repository-mismatch")
    return {"verified": not failures, "failures": failures, "run": run, "pull": pull}
