"""Cross-service schema definitions for Manim Video Generation Module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode:
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    GEOMETRY_VALIDATION_FAILED = "GEOMETRY_VALIDATION_FAILED"
    MANIM_UNAVAILABLE = "MANIM_UNAVAILABLE"
    MANIM_REQUEST_FAILED = "MANIM_REQUEST_FAILED"
    MANIM_RENDER_FAILED = "MANIM_RENDER_FAILED"
    MANIM_TIMEOUT = "MANIM_TIMEOUT"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class StructuredError(BaseModel):
    """Machine-readable and user-facing structured error format."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(default=ErrorCode.INTERNAL_ERROR, description="Standard error code")
    message: str = Field(default="An unexpected error occurred.", description="User-safe error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Safe additional error context")

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            res["details"] = self.details
        return res


class GeometryObject(BaseModel):
    """A single geometric entity to be visualized in Manim."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(description="Geometry type: circle, triangle, line, point, polygon, pyramid, prism, etc.")
    label: Optional[str] = Field(default=None, description="Identifier or label: A, B, C, S, O, etc.")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Coordinates, dimensions, colors, or constraints (e.g. {'coordinates': [0, 0, 0]})",
    )


class AnimationDirective(BaseModel):
    """One animation beat requested by the Math Agent."""

    model_config = ConfigDict(extra="ignore")

    action: str = Field(description="Animation action: draw, highlight, transform, fade_in, fade_out, write, rotate_camera, etc.")
    targets: List[str] = Field(default_factory=list, description="Labels or names of geometry objects involved")
    narration: Optional[str] = Field(default=None, description="Voiceover/explanation for this beat")
    duration_hint: Optional[float] = Field(default=None, description="Estimated duration in seconds")


class VisualizationConfig(BaseModel):
    """Configuration for presentation, camera framing, and visualization styling."""

    model_config = ConfigDict(extra="ignore")

    show_axes: bool = Field(default=False, description="Whether to display coordinate axes in rendering")
    is_3d: bool = Field(default=False, description="Whether rendering is in 3D perspective mode")
    camera_position: Optional[List[float]] = Field(default=None, description="Camera coordinates [x, y, z]")
    camera_orientation: Optional[Dict[str, float]] = Field(default=None, description="Camera orientation angles")
    scale_factor: float = Field(default=1.0, description="Display scale factor for visualization zoom")
    center_focus: Optional[List[float]] = Field(default=None, description="Center point of camera focus")
    show_labels: bool = Field(default=True, description="Whether to show point/vertex labels")
    quality: Literal["480p", "720p", "1080p"] = "720p"
    format: Literal["mp4", "gif"] = "mp4"
    language: str = Field(default="vi", description="Language code: vi, en, ...")


class OutputConfig(BaseModel):
    """Legacy Output configuration kept for backward compatibility."""

    model_config = ConfigDict(extra="ignore")

    quality: Literal["480p", "720p", "1080p"] = "720p"
    format: Literal["mp4", "gif"] = "mp4"
    language: str = Field(default="vi", description="Language code: vi, en, ...")
    show_axes: bool = False


class VisualizationSpec(BaseModel):
    """Standardized Visualization Specification sent from Math Agent to Manim Module."""

    model_config = ConfigDict(extra="ignore")

    problem: str = Field(description="Math problem description or theorem statement")
    solution_steps: List[str] = Field(
        default_factory=list,
        description="Ordered list of reasoning or solution steps",
    )
    geometry: List[GeometryObject] = Field(
        default_factory=list,
        description="List of geometric entities with solved coordinates",
    )
    animations: List[AnimationDirective] = Field(
        default_factory=list,
        description="Animation directives and narration beats",
    )
    config: VisualizationConfig = Field(default_factory=VisualizationConfig)
    output_config: OutputConfig = Field(default_factory=OutputConfig)

    @property
    def show_axes(self) -> bool:
        return self.config.show_axes or self.output_config.show_axes

    def to_prompt(self) -> str:
        """Serializes the spec into a structured prompt for the Manim Agent."""
        parts = [f"Chủ đề / Đề bài: {self.problem}"]
        if self.config.show_axes:
            parts.append("Hiển thị hệ trục tọa độ: BẬT (show_axes=True)")
        if self.solution_steps:
            parts.append("Các bước giải thích / chứng minh chi tiết:")
            for idx, step in enumerate(self.solution_steps, 1):
                parts.append(f"  {idx}. {step}")
        if self.geometry:
            parts.append("Các đối tượng hình học / tọa độ giải được:")
            for obj in self.geometry:
                label_str = f" ({obj.label})" if obj.label else ""
                props_str = f" - thuộc tính: {obj.properties}" if obj.properties else ""
                parts.append(f"  - {obj.type}{label_str}{props_str}")
        if self.animations:
            parts.append("Chỉ dẫn hoạt họa (animation beats):")
            for idx, anim in enumerate(self.animations, 1):
                targets_str = f" [đối tượng: {', '.join(anim.targets)}]" if anim.targets else ""
                narr_str = f" | Lời thoại: '{anim.narration}'" if anim.narration else ""
                parts.append(f"  - Beat {idx}: {anim.action}{targets_str}{narr_str}")
        return "\n".join(parts)


class MathRenderRequest(BaseModel):
    """Payload for POST /v1/math/generate."""

    model_config = ConfigDict(extra="ignore")

    spec: VisualizationSpec
    callback_url: Optional[str] = None


class MathRenderResponse(BaseModel):
    """Response from Manim Module for render job status."""

    model_config = ConfigDict(extra="ignore")

    job_id: Union[UUID, str] = Field(description="Identifier for tracking the generation & rendering job")
    project_id: Optional[Union[UUID, str]] = None
    status: Literal["queued", "generating", "rendering", "completed", "failed"] = "queued"
    video_url: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[Union[StructuredError, Dict[str, Any], str]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed")

    def get_error_code(self) -> Optional[str]:
        if isinstance(self.error, StructuredError):
            return self.error.code
        elif isinstance(self.error, dict):
            return self.error.get("code")
        elif isinstance(self.error, str):
            return ErrorCode.INTERNAL_ERROR
        return None

    def get_error_message(self) -> Optional[str]:
        if isinstance(self.error, StructuredError):
            return self.error.message
        elif isinstance(self.error, dict):
            return self.error.get("message")
        elif isinstance(self.error, str):
            return self.error
        return None

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get access for backward compatibility."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Dict-like bracket access for backward compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump(mode="json")
        if isinstance(self.error, StructuredError):
            data["error"] = self.error.to_dict()
        return data


def build_visualization_spec(
    problem_text: Union[str, Dict[str, Any]] = "",
    solution_steps: Optional[List[str]] = None,
    coordinates: Optional[Dict[str, Any]] = None,
    engine_result: Optional[Dict[str, Any]] = None,
    semantic_data: Optional[Dict[str, Any]] = None,
    is_3d: bool = False,
    show_axes: bool = False,
    quality: Literal["480p", "720p", "1080p"] = "720p",
) -> VisualizationSpec:
    """
    Automated Builder: Converts MathSolver internal geometry data, coordinates,
    drawing phases, and solution steps into a standard VisualizationSpec.
    Supports either explicit keyword parameters or a single geometry_data dict.
    """
    if isinstance(problem_text, dict):
        data = problem_text
        problem_text = (
            data.get("problem")
            or data.get("problem_text")
            or (data.get("semantic") or {}).get("input_text")
            or data.get("geometry_dsl")
            or "Minh họa hình học và các bước giải toán"
        )
        sol = data.get("solution")
        if isinstance(sol, dict):
            solution_steps = sol.get("steps") or []
        elif isinstance(sol, list):
            solution_steps = sol
        elif isinstance(sol, str):
            solution_steps = [s.strip() for s in sol.split("\n") if s.strip()]
        else:
            solution_steps = data.get("solution_steps") or []

        coordinates = data.get("coordinates") or {}
        engine_result = data
        semantic_data = data.get("semantic") or data.get("semantic_data")
        is_3d = bool(data.get("is_3d", False))
        show_axes = bool(data.get("show_axes", show_axes))
        if "quality" in data and data["quality"] in ("480p", "720p", "1080p"):
            quality = data["quality"]

    coords = coordinates or {}
    steps = solution_steps or []
    engine_res = engine_result or {}
    geometry_objs: List[GeometryObject] = []
    animation_beats: List[AnimationDirective] = []

    # 1. Add Point Objects with Solved Coordinates (Mathematical geometry preserved)
    for pt_name, pt_coords in coords.items():
        geometry_objs.append(
            GeometryObject(
                type="point_3d" if is_3d else "point_2d",
                label=pt_name,
                properties={"coordinates": pt_coords},
            )
        )

    # 2. Add Solids / Polygons
    solids = engine_res.get("solids", [])
    for solid in solids:
        geometry_objs.append(
            GeometryObject(
                type=solid.get("type", "solid_3d"),
                label=f"{solid.get('type')}_{'_'.join(solid.get('points', []))}",
                properties=solid,
            )
        )

    # 3. Add Circles
    circles = engine_res.get("circles", [])
    for c in circles:
        geometry_objs.append(
            GeometryObject(
                type="circle",
                label=f"circle_{c.get('center')}",
                properties=c,
            )
        )

    # 4. Construct Animation Beats from Drawing Phases and Solution Steps
    drawing_phases = engine_res.get("drawing_phases", [])
    if drawing_phases:
        for phase in drawing_phases:
            pts = phase.get("points", [])
            segs = phase.get("segments", [])
            seg_names = [f"{s[0]}{s[1]}" for s in segs]
            animation_beats.append(
                AnimationDirective(
                    action="draw",
                    targets=pts + seg_names,
                    narration=f"Dựng {phase.get('label', 'các điểm và đoạn thẳng')}: {', '.join(pts)}.",
                    duration_hint=2.5,
                )
            )

    if is_3d:
        animation_beats.append(
            AnimationDirective(
                action="rotate_camera",
                targets=["scene_3d"],
                narration="Quan sát khối đa diện trong không gian 3 chiều.",
                duration_hint=3.0,
            )
        )

    for idx, step in enumerate(steps):
        animation_beats.append(
            AnimationDirective(
                action="write",
                targets=[f"step_{idx+1}"],
                narration=step,
                duration_hint=3.5,
            )
        )

    vis_config = VisualizationConfig(
        show_axes=show_axes,
        is_3d=is_3d,
        quality=quality,
        format="mp4",
        language="vi",
    )
    legacy_output = OutputConfig(
        quality=quality,
        format="mp4",
        language="vi",
        show_axes=show_axes,
    )

    return VisualizationSpec(
        problem=problem_text,
        solution_steps=steps,
        geometry=geometry_objs,
        animations=animation_beats,
        config=vis_config,
        output_config=legacy_output,
    )
