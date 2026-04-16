import json
import logging
from typing import Any, Dict

from agents.geometry_agent import GeometryAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.ocr_agent import OCRAgent
from agents.parser_agent import ParserAgent
from agents.solver_agent import SolverAgent
from app.logutil import log_step
from app.ocr_celery import ocr_from_image_url
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine

logger = logging.getLogger(__name__)

_CLIP = 2000


def _clip(val: Any, n: int = _CLIP) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        s = val
    else:
        s = json.dumps(val, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"


def _step_io(step: str, input_val: Any = None, output_val: Any = None) -> None:
    """Debug: chỉ input/output (đã cắt), tránh dump dài dòng không cần thiết."""
    log_step(step, input=_clip(input_val), output=_clip(output_val))


class Orchestrator:
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.geometry_agent = GeometryAgent()
        self.ocr_agent = OCRAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.solver_agent = SolverAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()

    def _generate_step_description(self, semantic_json: Dict[str, Any], engine_result: Dict[str, Any]) -> str:
        """Tạo mô tả từng bước vẽ dựa trên kết quả của engine."""
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
        image_url: str = None,
        job_id: str = None,
        session_id: str = None,
        status_callback=None,
        history: list = None,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline. Optional history allows context-aware solving.
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
            # Look for the last assistant message with geometry data
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

        for attempt in range(MAX_RETRIES + 1):
            _step_io(
                "attempt",
                input_val=f"{attempt + 1}/{MAX_RETRIES + 1}",
                output_val=None,
            )
            if status_callback:
                await status_callback("solving")

            # Parser with context
            _step_io("step2_parse", input_val=f"{input_text[:50]}...", output_val=None)
            semantic_json = await self.parser_agent.process(input_text, feedback=feedback, context=previous_context)
            semantic_json["input_text"] = input_text
            _step_io("step2_parse", input_val=None, output_val=semantic_json)

            # Knowledge augmentation
            _step_io("step3_knowledge", input_val=semantic_json, output_val=None)
            semantic_json = self.knowledge_agent.augment_semantic_data(semantic_json)
            _step_io("step3_knowledge", input_val=None, output_val=semantic_json)

            # Geometry DSL with context (passing previous DSL to guide generation)
            _step_io("step4_geometry_dsl", input_val=semantic_json, output_val=None)
            dsl_code = await self.geometry_agent.generate_dsl(
                semantic_json, 
                previous_dsl=previous_context["geometry_dsl"] if previous_context else None
            )
            _step_io("step4_geometry_dsl", input_val=None, output_val=dsl_code)

            _step_io("step5_dsl_parse", input_val=dsl_code, output_val=None)
            points, constraints, is_3d = self.dsl_parser.parse(dsl_code)
            _step_io(
                "step5_dsl_parse",
                input_val=None,
                output_val={
                    "points": len(points),
                    "constraints": len(constraints),
                    "is_3d": is_3d,
                },
            )

            _step_io("step6_solve", input_val=f"{len(points)} pts / {len(constraints)} cons (is_3d={is_3d})", output_val=None)
            import anyio
            engine_result = await anyio.to_thread.run_sync(self.solver_engine.solve, points, constraints, is_3d)

            if engine_result:
                coordinates = engine_result.get("coordinates")
                _step_io("step6_solve", input_val=None, output_val=coordinates)
                logger.info(
                    "[Orchestrator] geometry solved job_id=%s is_3d=%s n_coords=%d",
                    job_id,
                    is_3d,
                    len(coordinates) if isinstance(coordinates, dict) else 0,
                )
                break

            feedback = "Geometry solver failed to find a valid solution for the given constraints. Parallelism or lengths might be inconsistent."
            _step_io(
                "step6_solve",
                input_val=f"attempt {attempt + 1}",
                output_val=feedback,
            )
            if attempt == MAX_RETRIES:
                _step_io(
                    "orchestrate_abort",
                    input_val=None,
                    output_val="solver_exhausted_retries",
                )
                return {
                    "error": "Solver failed after multiple attempts.",
                    "last_dsl": dsl_code,
                }

        _step_io("orchestrate_done", input_val=job_id, output_val="success")

        # 8. Solution calculation (New in v5.1)
        solution = None
        if engine_result:
            _step_io("step8_solve_math", input_val=semantic_json.get("target_question"), output_val=None)
            solution = await self.solver_agent.solve(semantic_json, engine_result)
            _step_io("step8_solve_math", input_val=None, output_val=solution.get("answer"))

        final_analysis = self._generate_step_description(semantic_json, engine_result)

        status = "success"
        return {
            "status": status,
            "job_id": job_id,
            "geometry_dsl": dsl_code,
            "coordinates": coordinates,
            "polygon_order": engine_result.get("polygon_order", []),
            "circles": engine_result.get("circles", []),
            "lines": engine_result.get("lines", []),
            "rays": engine_result.get("rays", []),
            "drawing_phases": engine_result.get("drawing_phases", []),
            "semantic": semantic_json,
            "semantic_analysis": final_analysis,
            "solution": solution,
            "is_3d": is_3d,
        }
