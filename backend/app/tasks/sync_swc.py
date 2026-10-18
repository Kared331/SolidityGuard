"""SWC knowledge sync: snapshot-first, network only when refresh=True."""

import logging

from celery import shared_task

from app.database import get_sync_session
from app.models import VulnerabilityEntry
from app.services.chroma_client import get_vulnerability_collection
from app.services.embedding import get_embedding
from app.services.engine.swc_sync import SWCSyncEngine

logger = logging.getLogger("solidguard.tasks.sync_swc")


def _entry_text(entry: dict) -> str:
    parts = [entry["title"] or "", entry["description"]]
    if entry["code_example"]:
        parts.append(entry["code_example"])
    return "\n\n".join(parts)


def _entry_metadata(entry: dict) -> dict:
    # Chroma metadata values must be primitives, never None.
    return {
        "swc_id": entry["swc_id"],
        "title": entry["title"] or "",
        "severity": entry["severity"] or "",
    }


def _upsert_entries(session, entries: list[dict]) -> int:
    """Idempotent by swc_id: re-running sync must not duplicate entries."""
    written = 0
    for entry in entries:
        existing = session.query(VulnerabilityEntry).filter_by(swc_id=entry["swc_id"]).first()
        if existing:
            existing.title = entry["title"]
            existing.description = entry["description"]
            existing.severity = entry["severity"]
            existing.code_example = entry["code_example"]
        else:
            session.add(
                VulnerabilityEntry(
                    swc_id=entry["swc_id"],
                    title=entry["title"],
                    description=entry["description"],
                    severity=entry["severity"],
                    code_example=entry["code_example"],
                )
            )
        written += 1
    return written


@shared_task(name="app.tasks.sync_swc.sync_swc", bind=True)
def sync_swc(self, refresh: bool = False):
    try:
        self.update_state(state="PROGRESS", meta={"step": "fetch", "refresh": refresh})

        engine = SWCSyncEngine()
        result = engine.execute(refresh=refresh)

        with get_sync_session() as session:
            _upsert_entries(session, result["parsed_entries"])
            session.commit()

        # Step 2: Generate embeddings and store in ChromaDB
        self.update_state(state="PROGRESS", meta={"step": "embed"})
        collection = get_vulnerability_collection()
        for entry in result["parsed_entries"]:
            text = _entry_text(entry)
            try:
                embedding = get_embedding(text)
                collection.upsert(
                    ids=[entry["swc_id"]],
                    documents=[text],
                    metadatas=[_entry_metadata(entry)],
                    embeddings=[embedding],
                )
            except Exception:
                logger.warning("Failed to generate embedding for %s", entry["swc_id"])

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "complete",
                "entries_synced": result["entries_synced"],
                "source": result["source"],
                "kb_version": result["kb_version"],
            },
        )
        logger.info(
            "SWC sync completed: %d entries from %s (%s)",
            result["entries_synced"],
            result["source"],
            result["kb_version"],
        )
        return {
            "status": "completed",
            "entries_synced": result["entries_synced"],
            "source": result["source"],
            "kb_version": result["kb_version"],
        }

    except Exception:
        # P0-5: FAILURE 态交由 Celery 原生标记（手动 update_state 破坏结果协议）
        logger.exception("SWC sync failed")
        raise
