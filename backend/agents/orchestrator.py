import json
import logging
from typing import Any, Dict, Optional

from agents.geometry_parser_agent import GeometryParserAgent
from agents.deepmath_solver_agent import DeepMathSolverAgent
from agents.ocr_agent import OCRAgent
from app.logutil import log_step
from app.ocr_celery import ocr_from_image_url
from manim_client.client import ManimClient
from manim_client.schemas import build_visualization_spec
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.validator import GeometryValidator

logger = logging.getLogger(__name__)

_CLIP = 2000


def _clip(val: Any, n: int = _CLIP) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        s = val
    else:
        s = json.dumps(val, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"


def _step_io(step: str, input_val: Any = None, output_val: Any = None) -> None:
    log_step(step, input=_clip(input_val), output=_clip(output_val))


class Orchestrator:
    """
    Refactored AI Core Orchestrator (v6.2 - Manim Video Module & Validation Integration):
    - GeometryParserAgent (Merged semantic parser & DSL generator)
    - DSLParser & GeometryEngine (Deterministic coordinate & topology resolver)
    - GeometryValidator (Strict invariant & constraint validation)
    - DeepMathSolverAgent (Program-Aided sandboxed SymPy mathematical solver)
    - ManimClient (Cross-service VisualizationSpec & Video Generation)
    """

    def __init__(self):
        self.geometry_parser_agent = GeometryParserAgent()
        self.deepmath_solver = DeepMathSolverAgent()
        self.ocr_agent = OCRAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()
        self.geometry_validator = GeometryValidator()
        self.manim_client = ManimClient()

    def _generate_step_description(self, semantic_json: Dict[str, Any], engine_result: Dict[str, Any]) -> str:
        """Generates step-by-step drawing instructions based on engine results."""
        analysis = semantic_json.get("analysis", "")
        if not analysis:
            analysis = f"Giải bài toán về {semantic_json.get('type', 'hình học')}."

        steps = ["\n\n**Các bước dựng hình:**"]
        drawing_phases = engine_result.get("drawing_phases", [])

        for phase in drawing_phases:
            label = phase.get("label", f"Giai đoạn {phase['phase']}")
            points = ", ".join(phase.get("points", []))
            segments = ", ".join([f"{s[0]}{s[1]}" for s in phase.get("segments", [])])

            step_text = f"- **{label}**:"
            if points:
                step_text += f" Xác định các điểm {points}."
            if segments:
                step_text += f" Vẽ các đoạn thẳng {segments}."
            steps.append(step_text)

        circles = engine_result.get("circles", [])
        for c in circles:
            steps.append(f"- **Đường tròn**: Vẽ đường tròn tâm {c['center']} bán kính {c['radius']}.")

        return analysis + "\n".join(steps)

    async def run(
        self,
        text: str,
        image_url: Optional[str] = None,
        job_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status_callback=None,
        history: Optional[list] = None,
        generate_video: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs the streamlined v6.1 AI Core pipeline with Manim Video Module integration.
        """
        _step_io(
            "orchestrate_start",
            input_val={
                "job_id": job_id,
                "text_len": len(text or ""),
                "image_url": image_url,
                "history_len": len(history or []),
            },
            output_val=None,
        )

        if status_callback:
            await status_callback("processing")

        # 1. Extract context from history (if any)
        previous_context = None
        if history:
            for msg in reversed(history):
                if msg.get("role") == "assistant" and msg.get("metadata", {}).get("geometry_dsl"):
                    previous_context = {
                        "geometry_dsl": msg["metadata"]["geometry_dsl"],
                        "coordinates": msg["metadata"].get("coordinates", {}),
                        "analysis": msg.get("content", ""),
                    }
                    break

        if previous_context:
            _step_io("context_found", input_val=None, output_val={"dsl_len": len(previous_context["geometry_dsl"])})

        # 2. Gather input text (OCR or direct)
        input_text = text
        if image_url:
            input_text = await ocr_from_image_url(image_url, self.ocr_agent)
            _step_io("step1_ocr", input_val=image_url, output_val=input_text)
        else:
            _step_io("step1_ocr", input_val="(no image)", output_val=text)

        feedback = None
        MAX_RETRIES = 2
        engine_result = None
        coordinates = {}
        is_3d = False
        dsl_code = ""
        semantic_json: Dict[str, Any] = {}

        # 3. GeometryParserAgent Loop (Semantic Parsing + DSL Generation)
        for attempt in range(MAX_RETRIES + 1):
            _step_io("attempt", input_val=f"{attempt + 1}/{MAX_RETRIES + 1}", output_val=None)
            if status_callback:
                await status_callback("solving")

            _step_io("step2_geometry_parse", input_val=f"{input_text[:60]}...", output_val=None)
            semantic_json = await self.geometry_parser_agent.process(
                input_text, feedback=feedback, context=previous_context
            )
            semantic_json["input_text"] = input_text
            dsl_code = semantic_json.get("geometry_dsl", "")
            _step_io("step2_geometry_parse", input_val=None, output_val=semantic_json)

            if not dsl_code:
                dsl_code = f"// Problem text: {input_text}"

            _step_io("step3_dsl_parse", input_val=dsl_code, output_val=None)
            points, constraints, is_3d = self.dsl_parser.parse(dsl_code)
            _step_io(
                "step3_dsl_parse",
                input_val=None,
                output_val={
                    "points": len(points),
                    "constraints": len(constraints),
                    "is_3d": is_3d,
                },
            )

            # 4. Geometry Solver Engine
            _step_io("step4_solve_geometry", input_val=f"{len(points)} pts / {len(constraints)} cons (is_3d={is_3d})", output_val=None)
            import anyio
            engine_result = await anyio.to_thread.run_sync(self.solver_engine.solve, points, constraints, is_3d)

            if engine_result:
                coordinates = engine_result.get("coordinates", {})
                _step_io("step4_solve_geometry", input_val=None, output_val=coordinates)

                # Validate geometry against mathematical invariants and constraints
                val_res = self.geometry_validator.validate(engine_result, constraints, is_3d)
                _step_io(
                    "step4_validate_geometry",
                    input_val=f"{val_res.checked_count} constraints checked",
                    output_val={"is_valid": val_res.is_valid, "errors": val_res.errors[:3]},
                )

                if val_res.is_valid:
                    logger.info(
                        "[Orchestrator] geometry solved and validated job_id=%s is_3d=%s n_coords=%d",
                        job_id,
                        is_3d,
                        len(coordinates) if isinstance(coordinates, dict) else 0,
                    )
                    break
                else:
                    feedback = f"Geometry validation failed: {val_res.error_summary}. Please correct the DSL to satisfy all constraints."
                    _step_io("step4_validate_geometry", input_val=f"attempt {attempt + 1}", output_val=feedback)
            else:
                feedback = "Geometry solver failed to find a valid solution for the given constraints. Parallelism or lengths might be inconsistent."
                _step_io("step4_solve_geometry", input_val=f"attempt {attempt + 1}", output_val=feedback)

            if attempt == MAX_RETRIES:
                _step_io("orchestrate_abort", input_val=None, output_val="solver_exhausted_retries")
                return {
                    "error": "Solver failed after multiple attempts.",
                    "last_dsl": dsl_code,
                }

        # 5. DeepMath Solver (Program-Aided Sandboxed SymPy Reasoning)
        solution = None
        _step_io("step5_deepmath_solve", input_val=semantic_json.get("target_question"), output_val=None)
        solution = await self.deepmath_solver.solve(
            problem_text=input_text,
            target_question=semantic_json.get("target_question"),
            semantic_data=semantic_json,
            geometry_context=engine_result,
        )
        _step_io("step5_deepmath_solve", input_val=None, output_val=solution.get("answer"))

        final_analysis = self._generate_step_description(semantic_json, engine_result or {})

        # 6. Build VisualizationSpec and initiate Manim Video Generation (Async)
        visualization_info = None
        if generate_video:
            try:
                _step_io("step6_build_visualization_spec", input_val=None, output_val="building")
                spec = build_visualization_spec(
                    problem_text=input_text,
                    solution_steps=solution.get("steps", []) if solution else [],
                    coordinates=coordinates,
                    engine_result=engine_result,
                    semantic_data=semantic_json,
                    is_3d=is_3d,
                )
                _step_io(
                    "step6_build_visualization_spec",
                    input_val=None,
                    output_val={
                        "geometry_objects": len(spec.geometry),
                        "animation_beats": len(spec.animations),
                    },
                )

                # Submit job to Manim Video Module
                render_resp = await self.manim_client.submit_render_job(spec)
                render_dict = render_resp.to_dict()
                visualization_info = {
                    "spec": spec.model_dump(mode="json"),
                    "job_id": str(render_resp.job_id),
                    "project_id": str(render_resp.project_id) if render_resp.project_id else None,
                    "status": render_resp.status,
                    "video_url": render_resp.video_url,
                    "error": render_dict.get("error"),
                }
                _step_io(
                    "step7_manim_job_submitted",
                    input_val=str(render_resp.job_id),
                    output_val=render_resp.status,
                )
            except Exception as e:
                logger.warning(f"[Orchestrator] Failed to package VisualizationSpec / contact Manim: {e}")
                visualization_info = {
                    "status": "failed",
                    "error": str(e),
                }

        _step_io("orchestrate_done", input_val=job_id, output_val="success")

        return {
            "status": "success",
            "job_id": job_id,
            "geometry_dsl": dsl_code,
            "coordinates": coordinates,
            "polygon_order": (engine_result or {}).get("polygon_order", []),
            "circles": (engine_result or {}).get("circles", []),
            "solids": (engine_result or {}).get("solids", []),
            "faces": (engine_result or {}).get("faces", []),
            "lines": (engine_result or {}).get("lines", []),
            "rays": (engine_result or {}).get("rays", []),
            "drawing_phases": (engine_result or {}).get("drawing_phases", []),
            "visualization_graph": (engine_result or {}).get("visualization_graph"),
            "geometry_objects": (engine_result or {}).get("geometry_objects", []),
            "auxiliary": (engine_result or {}).get("auxiliary", []),
            "semantic": semantic_json,
            "semantic_analysis": final_analysis,
            "solution": solution,
            "visualization": visualization_info,
            "is_3d": is_3d,
        }
