"""Job poll normalization for FE contract."""

import uuid

from app.job_poll import normalize_job_row_for_client


def test_normalize_adds_job_id_and_parses_result_json_string():
    jid = str(uuid.uuid4())
    row = {
        "id": jid,
        "status": "success",
        "user_id": uuid.uuid4(),
        "session_id": uuid.uuid4(),
        "result": '{"coordinates": {"A": [0, 1]}}',
        "input_text": "x",
    }
    out = normalize_job_row_for_client(row)
    assert out["job_id"] == jid
    assert out["id"] == jid
    assert out["status"] == "success"
    assert isinstance(out["result"], dict)
    assert out["result"]["coordinates"]["A"] == [0, 1]
    assert isinstance(out["user_id"], str)
    assert isinstance(out["session_id"], str)


def test_normalize_keeps_dict_result():
    row = {"id": "j1", "status": "processing", "result": None}
    out = normalize_job_row_for_client(row)
    assert out["job_id"] == "j1"
    assert out["result"] is None
