"""Unit tests for P1 Job State Machine & P2 Celery tasks."""

import pytest
from app.models.job_state import (
    JobStatus,
    JobStage,
    JobStateMachine,
    InvalidStateTransitionError,
    STAGE_PROGRESS_MAP,
)
from app.job_poll import normalize_job_row_for_client


def test_job_state_machine_valid_transitions():
    assert JobStateMachine.can_transition(JobStatus.CREATED, JobStatus.QUEUED)
    assert JobStateMachine.can_transition(JobStatus.QUEUED, JobStatus.PROCESSING)
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.COMPLETED)
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.FAILED)
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.DEGRADED)


def test_job_state_machine_invalid_transitions():
    assert not JobStateMachine.can_transition(JobStatus.COMPLETED, JobStatus.PROCESSING)
    assert not JobStateMachine.can_transition(JobStatus.FAILED, JobStatus.COMPLETED)
    assert not JobStateMachine.can_transition(JobStatus.CANCELLED, JobStatus.PROCESSING)

    with pytest.raises(InvalidStateTransitionError):
        JobStateMachine.validate_transition(JobStatus.COMPLETED, JobStatus.PROCESSING)


def test_job_state_machine_normalization():
    assert JobStateMachine.normalize_status("success") == JobStatus.COMPLETED
    assert JobStateMachine.normalize_status("error") == JobStatus.FAILED
    assert JobStateMachine.normalize_status("rendering_queued") == JobStatus.QUEUED
    assert JobStateMachine.normalize_status("geometry") == JobStatus.PROCESSING


def test_normalize_job_row_for_client():
    raw_row = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "geometry",
        "result": '{"coordinates": {"A": [0, 0]}}',
        "user_id": "user-uuid",
        "session_id": "session-uuid",
    }
    normalized = normalize_job_row_for_client(raw_row)
    assert normalized["job_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert normalized["status"] == "processing"
    assert normalized["stage"] == "geometry"
    assert normalized["progress"] == STAGE_PROGRESS_MAP[JobStage.GEOMETRY]
    assert isinstance(normalized["result"], dict)
    assert normalized["result"]["coordinates"]["A"] == [0, 0]
