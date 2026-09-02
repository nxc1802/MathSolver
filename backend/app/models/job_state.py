"""Formalized Job State Machine & Lifecycle Definitions for MathSolver."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    OCR = "ocr"
    PARSING = "parsing"
    GEOMETRY = "geometry"
    SOLVING = "solving"
    RENDERING = "rendering"


# Canonical progression of stages with default estimated progress percentages
STAGE_PROGRESS_MAP: Dict[JobStage, int] = {
    JobStage.OCR: 15,
    JobStage.PARSING: 35,
    JobStage.GEOMETRY: 65,
    JobStage.SOLVING: 85,
    JobStage.RENDERING: 95,
}

# Valid State Transitions
VALID_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.CREATED: {
        JobStatus.CREATED,
        JobStatus.QUEUED,
        JobStatus.PROCESSING,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    },
    JobStatus.QUEUED: {
        JobStatus.QUEUED,
        JobStatus.PROCESSING,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    },
    JobStatus.PROCESSING: {
        JobStatus.PROCESSING,
        JobStatus.COMPLETED,
        JobStatus.DEGRADED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    },
    # Terminal states
    JobStatus.COMPLETED: {JobStatus.COMPLETED},
    JobStatus.FAILED: {JobStatus.FAILED},
    JobStatus.DEGRADED: {JobStatus.DEGRADED},
    JobStatus.CANCELLED: {JobStatus.CANCELLED},
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal job state transition is attempted."""
    pass


class JobStateMachine:
    """Validator and manager for job lifecycle transitions."""

    @staticmethod
    def normalize_status(raw_status: Optional[str]) -> JobStatus:
        if not raw_status:
            return JobStatus.PROCESSING
        raw = raw_status.lower().strip()
        # Aliases for backward compatibility
        if raw in ("success", "done", "finished", "completed"):
            return JobStatus.COMPLETED
        if raw in ("error", "failed", "failure"):
            return JobStatus.FAILED
        if raw in ("rendering_queued", "queued"):
            return JobStatus.QUEUED
        if raw in ("rendering", "processing", "solving", "ocr", "parsing", "geometry"):
            return JobStatus.PROCESSING
        if raw == "cancelled":
            return JobStatus.CANCELLED
        if raw == "degraded":
            return JobStatus.DEGRADED
        return JobStatus.PROCESSING

    @staticmethod
    def normalize_stage(raw_stage: Optional[str]) -> Optional[JobStage]:
        if not raw_stage:
            return None
        raw = raw_stage.lower().strip()
        for stage in JobStage:
            if stage.value == raw:
                return stage
        return None

    @classmethod
    def can_transition(cls, current: JobStatus, target: JobStatus) -> bool:
        valid_targets = VALID_TRANSITIONS.get(current, set())
        return target in valid_targets

    @classmethod
    def validate_transition(cls, current_status: str | JobStatus, target_status: str | JobStatus) -> JobStatus:
        current = current_status if isinstance(current_status, JobStatus) else cls.normalize_status(current_status)
        target = target_status if isinstance(target_status, JobStatus) else cls.normalize_status(target_status)

        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(
                f"Invalid job state transition from {current.value} to {target.value}"
            )
        return target


class JobEventPayload(BaseModel):
    """Normalized payload broadcasted via WebSockets and returned by HTTP polling."""
    job_id: str
    status: JobStatus = JobStatus.PROCESSING
    stage: Optional[JobStage] = None
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    video_url: Optional[str] = None
