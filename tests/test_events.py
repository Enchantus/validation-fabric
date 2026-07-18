from pathlib import Path

import pytest

from validation_fabric.events import Event, EventError, append_event, reduce_status


def event(event_id: str, kind: str, domain: str = "") -> Event:
    return Event(1, event_id, kind, "head", f"2026-01-01T00:00:0{event_id[-1]}Z", domain=domain)


def test_exact_duplicate_is_idempotent_and_conflict_fails_closed(tmp_path: Path) -> None:
    original = event("evt-1", "candidate.created")
    assert append_event(tmp_path, original)["state"] == "appended"
    assert append_event(tmp_path, original)["state"] == "duplicate"
    with pytest.raises(EventError, match="conflicts"):
        append_event(tmp_path, event("evt-1", "candidate.rejected"))
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_status_reduction_is_ordered_and_candidate_scoped(tmp_path: Path) -> None:
    append_event(tmp_path, event("evt-1", "candidate.created"))
    append_event(tmp_path, event("evt-2", "domain.started", "python"))
    append_event(tmp_path, event("evt-3", "domain.completed", "python"))
    append_event(tmp_path, event("evt-4", "candidate.admitted"))
    append_event(
        tmp_path,
        Event(1, "other-1", "candidate.rejected", "other", "2026-01-01T00:00:05Z"),
    )
    assert reduce_status(tmp_path, "head") == {
        "schemaVersion": 1,
        "candidate": "head",
        "state": "admitted",
        "domains": {"python": "completed"},
        "eventCount": 4,
    }


def test_domain_event_requires_domain(tmp_path: Path) -> None:
    with pytest.raises(EventError, match="require a domain"):
        append_event(tmp_path, event("evt-1", "domain.started"))
