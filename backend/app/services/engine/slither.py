import json
import os
import subprocess

from app.services.engine.base import BaseEngine


def _build_detection_ref(detector: dict) -> str:
    check = detector.get("check", "unknown")
    elements = detector.get("elements", [])
    if elements:
        source_mapping = elements[0].get("source_mapping", {})
        filename = source_mapping.get("filename_relative", "")
        lines = source_mapping.get("lines", [])
        if lines:
            # Use range shorthand: "6-63" instead of "6-7-8-...-63"
            lines_str = f"{lines[0]}-{lines[-1]}" if len(lines) > 1 else str(lines[0])
        else:
            lines_str = "[]"
        ref = f"{check}:{filename}:{lines_str}"
        # Truncate to fit VARCHAR(500)
        if len(ref) > 490:
            ref = ref[:490] + "..."
        return ref
    return f"{check}:unknown:[]"


_FRAMEWORK_FILES = [
    "hardhat.config.js", "hardhat.config.ts",
    "foundry.toml",
    "truffle-config.js", "truffle-config.ts",
]
_DEP_DIRS = {"lib", "node_modules", "out", "cache", ".git", "test", "script", "artifacts"}


def _find_project_roots(top_dir: str) -> list[str]:
    """Find subdirectories containing framework config files."""
    roots = []
    for root, dirs, files in os.walk(top_dir):
        dirs[:] = [d for d in dirs if d not in _DEP_DIRS]
        for cfg in _FRAMEWORK_FILES:
            if cfg in files:
                roots.append(root)
                dirs.clear()
                break
    if not roots:
        roots.append(top_dir)
    return roots


def _has_framework_config(root: str) -> bool:
    """Check if the directory contains any framework config file."""
    return any(os.path.isfile(os.path.join(root, f)) for f in _FRAMEWORK_FILES)


def _needs_solc_fallback(project_root: str) -> bool:
    """Check if solc fallback is needed: Hardhat without npm deps, or no framework at all."""
    if not _has_framework_config(project_root):
        return True  # No framework config, use solc directly
    has_hardhat = any(
        os.path.isfile(os.path.join(project_root, f))
        for f in ["hardhat.config.js", "hardhat.config.ts"]
    )
    if has_hardhat:
        has_deps = os.path.isdir(os.path.join(project_root, "node_modules"))
        if not has_deps:
            return True  # Hardhat without npm deps
    return False


def _collect_sol_files(root_dir: str) -> list[str]:
    """Collect .sol files excluding dep dirs, sorted by size (small first)."""
    entries = []
    for r, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in _DEP_DIRS]
        for f in files:
            if f.endswith(".sol"):
                path = os.path.join(r, f)
                size = os.path.getsize(path)
                entries.append((size, path))
    entries.sort()  # smallest first for quick wins
    return [p for _, p in entries]


def _run_slither_file(sol_file: str, timeout: int = 90) -> dict:
    """Run slither on a single .sol file with solc framework."""
    try:
        proc = subprocess.run(
            ["slither", sol_file, "--compile-force-framework", "solc", "--json", "-"],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"error": proc.stderr or "Slither produced no output"}
    except subprocess.TimeoutExpired:
        return {"error": f"Slither timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse Slither output"}
    except FileNotFoundError:
        return {"error": "Slither binary not found"}


def _run_slither_dir(project_dir: str, timeout: int = 300) -> dict:
    """Run slither on a project directory (uses auto-detected framework)."""
    try:
        proc = subprocess.run(
            ["slither", project_dir, "--json", "-"],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"error": proc.stderr or "Slither produced no output"}
    except subprocess.TimeoutExpired:
        return {"error": f"Slither timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse Slither output"}
    except FileNotFoundError:
        return {"error": "Slither binary not found"}


class SlitherEngine(BaseEngine):
    def execute(self, project_id: int, project_dir: str) -> dict:
        if not os.path.isdir(project_dir):
            return {"raw_result": {}, "detections": [], "detection_count": 0}

        project_roots = _find_project_roots(project_dir)
        all_detectors = []
        first_result = {}

        for root in project_roots:
            if _needs_solc_fallback(root):
                # No framework or Hardhat without deps: analyze each .sol file with solc
                sol_files = _collect_sol_files(root)
                self.logger.info(
                    "Project %d: Hardhat without node_modules, analyzing %d files with solc",
                    project_id, len(sol_files),
                )
                for sf in sol_files:
                    self.logger.info("  Slither solc: %s", sf)
                    parsed = _run_slither_file(sf, timeout=90)
                    if not first_result:
                        first_result = parsed
                    dets = parsed.get("results", {}).get("detectors", [])
                    all_detectors.extend(dets)
            else:
                self.logger.info("Running Slither on %s for project %d", root, project_id)
                parsed = _run_slither_dir(root, timeout=300)
                first_result = parsed
                dets = parsed.get("results", {}).get("detectors", [])
                all_detectors.extend(dets)

        detections = []
        for det in all_detectors:
            detection_ref = _build_detection_ref(det)
            elements = det.get("elements", [])
            detections.append({
                "detection_ref": detection_ref,
                "check_name": det.get("check", "unknown"),
                "description": det.get("description", ""),
                "impact": det.get("impact"),
                "confidence": det.get("confidence"),
                "element_json": elements if elements else None,
            })

        return {
            "raw_result": first_result,
            "detections": detections,
            "detection_count": len(detections),
        }
