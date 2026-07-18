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
