import json
import logging
import os
import subprocess

from app.celery_app import celery
from app.database import get_sync_session
from app.models import AnalysisResult, Detection

logger = logging.getLogger("solidiguard.tasks.run_slither")


def _build_detection_ref(detector: dict) -> str:
    check = detector.get("check", "unknown")
    elements = detector.get("elements", [])
    if elements:
        source_mapping = elements[0].get("source_mapping", {})
        filename = source_mapping.get("filename_relative", "")
        lines = source_mapping.get("lines", [])
        lines_part = "-".join(str(x) for x in lines) if lines else "[]"
        return f"{check}:{filename}:{lines_part}"
    return f"{check}:unknown:[]"


@celery.task(name="run_slither", bind=True)
def run_slither(self, project_id: int) -> None:
    project_dir = os.path.join("uploads", str(project_id))
    if not os.path.isdir(project_dir):
        logger.error("Project directory not found: %s", project_dir)
        return

    try:
        proc = subprocess.run(
            ["slither", project_dir, "--json", "-"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            parsed = {"error": proc.stderr}
        else:
            parsed = json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        parsed = {"error": "Slither timed out after 300s"}
    except json.JSONDecodeError:
        parsed = {"error": "Failed to parse Slither output"}
    except FileNotFoundError:
        parsed = {"error": "Slither binary not found"}
    except Exception as e:
        logger.exception("Unexpected error running Slither for project %d", project_id)
        parsed = {"error": str(e)}

    try:
        with get_sync_session() as session:
            record = AnalysisResult(
                project_id=project_id,
                analyzer="slither",
                result_json=parsed,
            )
            session.add(record)
            session.flush()

            detectors = parsed.get("results", {}).get("detectors", [])
            for det in detectors:
                detection_ref = _build_detection_ref(det)
                elements = det.get("elements", [])
                session.add(
                    Detection(
                        analysis_result_id=record.id,
                        detection_ref=detection_ref,
                        check_name=det.get("check", "unknown"),
                        description=det.get("description", ""),
                        impact=det.get("impact"),
                        confidence=det.get("confidence"),
                        element_json=elements if elements else None,
                    )
                )

            session.commit()
            logger.info(
                "Slither analysis completed for project %d: %d detections",
                project_id,
                len(detectors),
            )
    except Exception:
        logger.exception("Failed to save Slither results for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
