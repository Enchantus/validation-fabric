"""The `vv` command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .certificates import Evidence, admit, authorize_merge_certificate
from .config import ConfigError, load_config
from .core import FabricError, build_plan, run_domain
from .events import Event, EventError, append_event, reduce_status
from .github import HttpGitHubApi
from .merge import decide_merge, result_exit_code


def _write(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _default_manifest(preset: str) -> str:
    commands = {
        "python": '["python", "-m", "pytest", "-q"]',
        "node": '["npm", "test"]',
        "go": '["go", "test", "./..."]',
        "polyglot": '["python", "-m", "pytest", "-q"]',
    }
    paths = {"python": '["**/*.py"]', "node": '["**/*.js", "**/*.ts"]', "go": '["**/*.go"]', "polyglot": '["**/*"]'}
    return f"""schemaVersion: 1
defaultBranch: main
fallbackDomains: [validation]
domains:
  - id: validation
    paths: {paths[preset]}
    inputs: [".validation-fabric.yml"]
    commands:
      - {commands[preset]}
    runner: ubuntu-latest
merge:
  enabled: false
  method: squash
"""


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="vv", description="Risk-aware exact-candidate validation")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument("--repo-root", default=".")
    result.add_argument("--config", default=".validation-fabric.yml")
    sub = result.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--preset", choices=("python", "node", "go", "polyglot"), default="python")
    sub.add_parser("doctor")
    for name in ("plan", "run", "status", "admit"):
        command = sub.add_parser(name)
        command.add_argument("--base", default="origin/main")
        command.add_argument("--head", default="HEAD")
        if name == "run":
            command.add_argument("--domain", action="append")
        if name == "admit":
            command.add_argument("--evidence-dir", required=True)
            command.add_argument("--repository", required=True)
            command.add_argument("--run-id", required=True, type=int)
            command.add_argument("--pull-request", required=True, type=int)
            command.add_argument("--key-env", default="VALIDATION_FABRIC_CERTIFICATE_KEY")
        if name == "status":
            command.add_argument("--event-dir")
            command.add_argument("--candidate")
    event = sub.add_parser("event")
    event.add_argument("kind")
    event.add_argument("--event-id", required=True)
    event.add_argument("--candidate", required=True)
    event.add_argument("--occurred-at", required=True)
    event.add_argument("--domain", default="")
    event.add_argument("--repository", default="local")
    event.add_argument("--run-id", type=int, default=0)
    event.add_argument("--metadata-json", default="{}")
    event.add_argument("--event-dir", default=".validation-fabric/events")
    explain = sub.add_parser("explain")
    explain.add_argument("domain")
    merge = sub.add_parser("merge")
    merge.add_argument("--repository", required=True)
    merge.add_argument("--pull-request", required=True, type=int)
    merge.add_argument("--admitted-head", required=True)
    merge.add_argument("--certificate", required=True)
    merge.add_argument("--key-env", default="VALIDATION_FABRIC_CERTIFICATE_KEY")
    merge.add_argument("--token-env", default="GITHUB_TOKEN")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    manifest = root / args.config
    try:
        if args.command == "init":
            if manifest.exists():
                raise ConfigError(f"configuration already exists: {manifest}")
            manifest.write_text(_default_manifest(args.preset), encoding="utf-8")
            _write({"schemaVersion": 1, "created": str(manifest), "preset": args.preset})
            return 0
        if args.command == "event":
            metadata = json.loads(args.metadata_json)
            if not isinstance(metadata, dict):
                raise ValueError("metadata-json must contain an object")
            result = append_event(
                root / args.event_dir,
                Event(
                    1,
                    args.event_id,
                    args.kind,
                    args.candidate,
                    args.occurred_at,
                    args.repository,
                    args.run_id,
                    args.domain,
                    metadata,
                ),
            )
            _write(result)
            return 0
        if args.command == "status" and args.event_dir:
            if not args.candidate:
                raise ValueError("status --event-dir requires --candidate")
            _write(reduce_status(root / args.event_dir, args.candidate))
            return 0
        config = load_config(manifest)
        if args.command == "doctor":
            _write(
                {
                    "schemaVersion": 1,
                    "ok": True,
                    "defaultBranch": config.default_branch,
                    "domains": sorted(config.domains),
                    "mergeEnabled": config.merge.enabled,
                }
            )
            return 0
        if args.command == "explain":
            if args.domain not in config.domains:
                raise ConfigError(f"unknown domain: {args.domain}")
            domain = config.domains[args.domain]
            _write(
                {
                    "schemaVersion": 1,
                    "domain": domain.id,
                    "paths": domain.paths,
                    "inputs": domain.inputs,
                    "commands": domain.commands,
                    "requires": domain.requires,
                    "cwd": domain.cwd,
                    "runner": domain.runner,
                    "toolchain": domain.toolchain,
                }
            )
            return 0
        if args.command == "merge":
            token = os.environ.get(args.token_env, "")
            if not token:
                raise ValueError(f"token environment variable is empty: {args.token_env}")
            key = os.environ.get(args.key_env, "")
            if not key:
                raise ValueError(f"key environment variable is empty: {args.key_env}")
            envelope = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
            authorization = authorize_merge_certificate(
                envelope, key, args.repository, args.admitted_head, args.pull_request
            )
            if not authorization["authorized"]:
                _write({"action": "reject", **authorization})
                return 1
            result = decide_merge(
                HttpGitHubApi(args.repository, token),
                config,
                args.pull_request,
                args.admitted_head,
                authorization["base"],
            )
            _write(result)
            return result_exit_code(result)
        plan = build_plan(root, config, args.base, args.head)
        plan_dict = plan.to_dict()
        if args.command in {"plan", "status"}:
            _write(plan_dict)
            return 0
        if plan.state == "superseded" and args.command != "admit":
            _write(plan_dict)
            return 0
        if args.command == "run":
            selected = set(args.domain or [record.domain for record in plan.domains])
            unknown = sorted(selected - config.domains.keys())
            if unknown:
                raise ConfigError(f"unknown domains: {', '.join(unknown)}")
            failed = False
            for record in plan.domains:
                if record.domain not in selected:
                    continue
                code, commands = run_domain(root, config.domains[record.domain], plan.changed)
                domain_evidence = Evidence(
                    1,
                    os.environ.get("GITHUB_REPOSITORY", "local"),
                    int(os.environ.get("GITHUB_RUN_ID", "0")),
                    plan.base,
                    plan.head,
                    record.domain,
                    record.fingerprint,
                    "pass" if code == 0 else "fail",
                    tuple(commands),
                )
                _write(domain_evidence.to_dict())
                failed |= code != 0
            return 1 if failed else 0
        evidence_items = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(Path(args.evidence_dir).rglob("*.json"))
            if path.name != "validation-fabric-plan.json"
        ]
        key = os.environ.get(args.key_env, "")
        envelope = admit(plan_dict, evidence_items, args.repository, args.run_id, key, args.pull_request)
        _write(envelope)
        return 0 if envelope["certificate"]["admitted"] else 1
    except (ConfigError, EventError, FabricError, ValueError, OSError, json.JSONDecodeError) as error:
        _write({"schemaVersion": 1, "ok": False, "error": str(error)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
