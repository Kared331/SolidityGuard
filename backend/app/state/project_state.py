from enum import StrEnum


class ProjectStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"


VALID_TRANSITIONS = {
    ProjectStatus.UPLOADED: {ProjectStatus.PROCESSING},
    ProjectStatus.PROCESSING: {ProjectStatus.READY},
}

AVAILABLE_ACTIONS = {
    ProjectStatus.UPLOADED: [],
    ProjectStatus.PROCESSING: [],
    ProjectStatus.READY: ["analyze", "fuzz", "llm-audit", "report"],
}


def validate_transition(current: ProjectStatus, target: ProjectStatus) -> bool:
    valid_targets = VALID_TRANSITIONS.get(current, set())
    return target in valid_targets


def get_available_actions(status: ProjectStatus) -> list[str]:
    return AVAILABLE_ACTIONS.get(status, [])
