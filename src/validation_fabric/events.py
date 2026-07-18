"""Atomic candidate lifecycle events and deterministic status reduction."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .certificates import canonical

EVENT_KINDS = {
    "candidate.created",
    "candidate.admitted",
    "candidate.rejected",
    "candidate.superseded",
    "domain.started",
    "domain.reused",
    "domain.completed",
    "domain.failed",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,160}$")


class EventError(ValueError):
    """Raised when an event conflicts with the append-only ledger."""


@dataclass(frozen=True)
class Event:
    schema_version: int
    event_id: str
    kind: str
    candidate: str
    occurred_at: str
    repository: str = "local"
    run_id: int = 0
    domain: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schemaVersion"] = value.pop("schema_version")
        value["eventId"] = value.pop("event_id")
        value["occurredAt"] = value.pop("occurred_at")
        value["runId"] = value.pop("run_id")
        return value


def validate_event(event: Event) -> None:
    if event.schema_version != 1:
        raise EventError("event schemaVersion must be 1")
    if not SAFE_ID.fullmatch(event.event_id):
        raise EventError("eventId must use 1-160 safe characters")
    if event.kind not in EVENT_KINDS:
        raise EventError(f"unsupported event kind: {event.kind}")
    if not event.candidate or not event.occurred_at:
        raise EventError("candidate and occurredAt are required")
    if event.kind.startswith("domain.") and not event.domain:
        raise EventError("domain events require a domain")


def append_event(directory: Path, event: Event) -> dict[str, Any]:
    validate_event(event)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{event.event_id}.json"
    encoded = canonical(event.to_dict()) + b"\n"
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
            temporary_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
            return {"schemaVersion": 1, "state": "appended", "event": event.to_dict()}
        except FileExistsError:
            existing = destination.read_bytes()
            if existing != encoded:
                raise EventError(f"eventId conflicts with existing event: {event.event_id}")
            return {"schemaVersion": 1, "state": "duplicate", "event": event.to_dict()}
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def reduce_status(directory: Path, candidate: str) -> dict[str, Any]:
    events = [_load_event(path) for path in directory.glob("*.json")]
    selected = sorted(
        (event for event in events if event["candidate"] == candidate),
        key=lambda event: (event["occurredAt"], event["eventId"]),
    )
    domains: dict[str, str] = {}
    state = "unknown"
    for event in selected:
        kind = event["kind"]
        if kind.startswith("candidate."):
            state = kind.split(".", 1)[1]
        elif event["domain"]:
            domains[event["domain"]] = kind.split(".", 1)[1]
    return {
        "schemaVersion": 1,
        "candidate": candidate,
        "state": state,
        "domains": dict(sorted(domains.items())),
        "eventCount": len(selected),
    }


def _load_event(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise EventError(f"invalid event file: {path.name}")
    required = ("eventId", "kind", "candidate", "occurredAt", "domain")
    if any(not isinstance(value.get(field), str) for field in required):
        raise EventError(f"invalid event fields: {path.name}")
    return value
