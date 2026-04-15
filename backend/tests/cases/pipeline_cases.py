"""Shared geometry pipeline test cases (single-session, multi-turn)."""

from __future__ import annotations

from typing import Any

QUERIES: list[dict[str, Any]] = [
    {
        "id": "Q1",
        "text": "Cho hình chữ nhật ABCD có AB bằng 5 và AD bằng 10",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q2",
        "text": "Tam giác ABC có AB=6, BC=8, AC=10",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 1,
    },
    {
        "id": "Q3",
        "text": "Cho hình chữ nhật ABCD có AB=10 và AD=20. Gọi M là trung điểm của cạnh AB.",
        "expect_pts": ["A", "B", "C", "D", "M"],
        "expect_phases": 2,
    },
    {
        "id": "Q4",
        "text": "Cho hình thang ABCD vuông tại A và D. AB=4, CD=8, AD=5.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q5",
        "text": "Cho hình vuông ABCD có cạnh bằng 6.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q6",
        "text": "Cho tam giác ABC vuông tại A. AB=3, AC=4. Vẽ đường cao AH.",
        "expect_pts": ["A", "B", "C", "H"],
        "expect_phases": 2,
    },
    {
        "id": "Q7",
        "text": "Cho hình thoi ABCD có cạnh bằng 5 và góc A bằng 60 độ.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q8",
        "text": "Cho đường tròn tâm O bán kính bằng 7.",
        "expect_pts": ["O"],
        "expect_phases": 1,
    },
    {
        "id": "Q9",
        "text": "Cho hình bình hành ABCD có AB=8, AD=6. Gọi E là trung điểm của CD. Vẽ đoạn thẳng AE.",
        "expect_pts": ["A", "B", "C", "D", "E"],
        "expect_phases": 2,
    },
    {
        "id": "Q10-Step1",
        "text": "Cho hình chữ nhật ABCD có AB=10, AD=5.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q11-Video",
        "text": "Cho tam giác ABC đều cạnh 5. Vẽ đường tròn ngoại tiếp tam giác.",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 2,
        "request_video": True,
    },
    {
        "id": "Q12-3D",
        "text": "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10, đường cao SO=15 với O là tâm đáy.",
        "expect_pts": ["S", "A", "B", "C", "D", "O"],
        "expect_phases": 2,
    },
]

Q10_FOLLOW_UP: dict[str, Any] = {
    "id": "Q10-Step2",
    "text": "Vẽ thêm đường chéo AC.",
    "expect_pts": ["A", "B", "C", "D"],
    "expect_phases": 2,
}

# Second multi-turn flow: follow-up depends on prior triangle definition in the same session.
Q13_HISTORY_STEPS: list[dict[str, Any]] = [
    {
        "id": "Q13-Step1",
        "text": "Cho tam giác ABC với AB=5, BC=6, AC=7.",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 1,
    },
    {
        "id": "Q13-Step2",
        "text": "Tính diện tích tam giác ABC (dùng các cạnh đã nêu ở trên).",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 1,
    },
]


def validate_q10_step2_dsl(dsl: str) -> bool:
    """Multi-turn rectangle + diagonal: merged DSL should still describe polygon and diagonal."""
    if not dsl:
        return False
    return "POLYGON_ORDER" in dsl and "SEGMENT" in dsl


def validate_query_result(q: dict[str, Any], result_data: dict[str, Any]) -> list[str]:
    """Return list of validation error strings (empty if pass)."""
    errors: list[str] = []
    coords = result_data.get("coordinates", {}) or {}
    for pt in q.get("expect_pts", []):
        if pt not in coords:
            errors.append(f"Missing point {pt}")
    if coords and len(coords) > 1 and all(v == [0, 0, 0] for v in coords.values()):
        errors.append("All points are at [0,0,0]")
    phases = result_data.get("drawing_phases", []) or []
    min_phases = int(q.get("expect_phases", 1))
    if len(phases) < min_phases:
        errors.append(f"Expected {min_phases} phases, got {len(phases)}")
    return errors
