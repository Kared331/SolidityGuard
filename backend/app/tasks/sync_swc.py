"""SWC knowledge sync with GitHub API auth (4.16) and error handling (4.14)."""

import logging

from celery import shared_task

from app.database import get_sync_session
from app.models import VulnerabilityEntry
from app.services.chroma_client import get_vulnerability_collection
from app.services.embedding import get_embedding
from app.services.engine.swc_sync import SWCSyncEngine

logger = logging.getLogger("solidguard.tasks.sync_swc")


@shared_task(name="app.tasks.sync_swc.sync_swc", bind=True)
def sync_swc(self):
    try:
        self.update_state(state="PROGRESS", meta={"step": "fetch"})

        engine = SWCSyncEngine()
        result = engine.execute()

        with get_sync_session() as session:
            for entry in result["parsed_entries"]:
                existing = (
                    session.query(VulnerabilityEntry)
                    .filter_by(swc_id=entry["swc_id"])
                    .first()
                )
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

            session.commit()

        # Step 2: Generate embeddings and store in ChromaDB
        self.update_state(state="PROGRESS", meta={"step": "embed"})
        collection = get_vulnerability_collection()
        for entry in result["parsed_entries"]:
            parts = [entry["title"] or "", entry["description"]]
            if entry["code_example"]:
                parts.append(entry["code_example"])
            text = "\n\n".join(parts)
            try:
                embedding = get_embedding(text)
                collection.upsert(
                    ids=[entry["swc_id"]],
                    documents=[text],
                    embeddings=[embedding],
                )
            except Exception:
                logger.warning("Failed to generate embedding for %s", entry["swc_id"])

        self.update_state(
            state="PROGRESS",
            meta={"step": "complete", "entries_synced": result["entries_synced"]},
        )
        logger.info("SWC sync completed: %d entries synced", result["entries_synced"])
        return {"status": "completed", "entries_synced": result["entries_synced"]}

    except Exception:
        # P0-5: FAILURE 态交由 Celery 原生标记（手动 update_state 破坏结果协议）
        logger.exception("SWC sync failed")
        raise
