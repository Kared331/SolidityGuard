"""SWC 知识库快照：完整性、版本号、默认不联网、幂等写入。"""

from unittest.mock import MagicMock

import pytest

from app.services.engine import swc_sync
from app.services.engine.swc_sync import (
    EXPECTED_ENTRIES,
    SWCSyncEngine,
    kb_version,
    load_snapshot,
    validate_entries,
)
from app.tasks.sync_swc import _entry_metadata, _entry_text, _upsert_entries

# ─── 快照完整性 ──────────────────────────────────────────────────


def test_snapshot_has_all_entries():
    entries = load_snapshot()

    assert len(entries) == EXPECTED_ENTRIES == 37
    assert len({e["swc_id"] for e in entries}) == 37
    assert all(e["title"] and e["description"] for e in entries)


def test_validate_rejects_wrong_count():
    with pytest.raises(ValueError, match="expected 37"):
        validate_entries([{"swc_id": "SWC-100", "title": "t", "description": "d"}])


def test_validate_rejects_missing_field():
    entries = [dict(e) for e in load_snapshot()]
    entries[0]["description"] = "   "

    with pytest.raises(ValueError, match="missing description"):
        validate_entries(entries)


# ─── 版本号 ──────────────────────────────────────────────────────


def test_kb_version_is_stable():
    first = kb_version()
    second = kb_version()

    assert first == second
    assert first.startswith("swc-")
    assert len(first) == len("swc-") + 8


def test_kb_version_changes_when_entry_changes():
    entries = [dict(e) for e in load_snapshot()]
    before = kb_version(entries)
    entries[0]["title"] = entries[0]["title"] + " (edited)"

    assert kb_version(entries) != before


# ─── 默认离线 ────────────────────────────────────────────────────


def test_default_execute_does_not_touch_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("default sync must not hit the network")

    monkeypatch.setattr(swc_sync.httpx, "get", _boom)

    result = SWCSyncEngine().execute()

    assert result["source"] == "snapshot"
    assert result["entries_synced"] == 37
    assert result["kb_version"].startswith("swc-")


def test_refresh_uses_fetched_entries(monkeypatch):
    edited = [dict(e) for e in load_snapshot()]
    edited[0]["title"] = "Refreshed Title"
    monkeypatch.setattr(SWCSyncEngine, "_fetch_and_parse", lambda self: edited)

    result = SWCSyncEngine().execute(refresh=True)

    assert result["source"] == "refresh"
    assert result["parsed_entries"][0]["title"] == "Refreshed Title"
    assert result["kb_version"] != kb_version()


# ─── Chroma 文档与 metadata ─────────────────────────────────────


def test_entry_metadata_has_no_none_values():
    entry = load_snapshot()[0]

    meta = _entry_metadata(entry)

    assert meta["swc_id"] == entry["swc_id"]
    assert meta["title"] == entry["title"]
    # severity is absent upstream -> "" (Chroma forbids None), never null
    assert all(isinstance(v, str) for v in meta.values())
    assert meta["title"]


def test_entry_text_contains_title_and_description():
    entry = load_snapshot()[0]

    text = _entry_text(entry)

    assert entry["title"] in text
    assert entry["description"][:40] in text


# ─── 幂等写入 ────────────────────────────────────────────────────


def test_upsert_inserts_new_entries():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    entries = load_snapshot()[:2]

    written = _upsert_entries(session, entries)

    assert written == 2
    assert session.add.call_count == 2


def test_upsert_updates_without_inserting():
    session = MagicMock()
    existing = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = existing
    entries = load_snapshot()[:2]

    written = _upsert_entries(session, entries)

    assert written == 2
    session.add.assert_not_called()
    assert existing.title == entries[-1]["title"]
