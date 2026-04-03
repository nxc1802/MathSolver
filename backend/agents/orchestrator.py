import json
import logging
from typing import Any, Dict

from app.logutil import log_step

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        from agents.ocr_agent import OCRAgent
        from agents.geometry_agent import GeometryAgent
        from agents.knowledge_agent import KnowledgeAgent
        from agents.parser_agent import ParserAgent
        from agents.renderer_agent import RendererAgent
        from solver.dsl_parser import DSLParser
        from solver.engine import GeometryEngine

        self.parser_agent = ParserAgent()
        self.geometry_agent = GeometryAgent()
        self.ocr_agent = OCRAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.renderer_agent = RendererAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()

    async def run(
        self,
        text: str,
        image_url: str = None,
        job_id: str = None,
        session_id: str = None,
        status_callback=None,
        request_video: bool = False,
    ) -> Dict[str, Any]:
        log_step(
            "orchestrate_start",
            job_id=job_id,
            text_len=len(text or ""),
            image_url=image_url,
            request_video=request_video,
        )

        if status_callback:
            await status_callback("processing")

        input_text = text
        if image_url:
            log_step("step1_ocr", phase="start", url=image_url)
            input_text = await self.ocr_agent.process_url(image_url)
            log_step(
                "step1_ocr",
                phase="done",
                output_chars=len(input_text or ""),
                output_preview=str(input_text)[:500],
            )
        else:
            log_step("step1_ocr", phase="skipped", reason="no_image_url")

        feedback = None
        MAX_RETRIES = 2

        for attempt in range(MAX_RETRIES + 1):
            log_step("attempt", n=attempt + 1, max=MAX_RETRIES + 1)
            if status_callback:
                await status_callback("solving")

            log_step("step2_parse", phase="start", input_preview=str(input_text)[:800])
            semantic_json = await self.parser_agent.process(input_text, feedback=feedback)
            semantic_json["input_text"] = input_text
            log_step(
                "step2_parse",
                phase="done",
                output=json.dumps(semantic_json, ensure_ascii=False, default=str)[:4000],
            )

            log_step("step3_knowledge", phase="start", input_keys=list(semantic_json.keys()))
            semantic_json = self.knowledge_agent.augment_semantic_data(semantic_json)
            log_step(
                "step3_knowledge",
                phase="done",
                output=json.dumps(semantic_json, ensure_ascii=False, default=str)[:4000],
            )

            log_step("step4_geometry_dsl", phase="start")
            dsl_code = await self.geometry_agent.generate_dsl(semantic_json)
            log_step("step4_geometry_dsl", phase="done", output=str(dsl_code)[:4000])

            log_step("step5_dsl_parse", phase="start")
            points, constraints = self.dsl_parser.parse(dsl_code)
            log_step(
                "step5_dsl_parse",
                phase="done",
                num_points=len(points),
                num_constraints=len(constraints),
            )

            log_step("step6_solve", phase="start")
            coordinates = self.solver_engine.solve(points, constraints)

            if coordinates:
                log_step(
                    "step6_solve",
                    phase="done",
                    coordinates=json.dumps(coordinates, ensure_ascii=False)[:2000],
                )
                break

            feedback = "Geometry solver failed to find a valid solution for the given constraints. Parallelism or lengths might be inconsistent."
            log_step("step6_solve", phase="failed", attempt=attempt + 1, feedback=feedback)
            if attempt == MAX_RETRIES:
                log_step("orchestrate_abort", reason="solver_exhausted_retries")
                return {
                    "error": "Solver failed after multiple attempts.",
                    "last_dsl": dsl_code,
                }

        status = "success"
        if request_video:
            log_step("step7_video", phase="start", job_id=job_id)
            try:
                from worker.celery_app import BROKER_URL
                from worker.tasks import render_geometry_video

                masked_broker = BROKER_URL.split("@")[-1] if "@" in BROKER_URL else BROKER_URL
                log_step("step7_video", celery_broker=masked_broker)

                result_payload = {
                    "geometry_dsl": dsl_code,
                    "coordinates": coordinates,
                    "semantic": semantic_json,
                    "semantic_analysis": semantic_json.get("input_text", ""),
                    "session_id": session_id,
                }
                task = render_geometry_video.delay(job_id, result_payload)
                status = "rendering_queued"
                log_step("step7_video", phase="queued", task_id=str(task.id))
            except Exception as e:
                logger.exception("Celery queue failed for job %s", job_id)
                log_step("step7_video", phase="error", error=str(e))
                status = "success"
        else:
            log_step("step7_video", phase="skipped")

        log_step(
            "orchestrate_done",
            job_id=job_id,
            status=status,
        )

        return {
            "status": status,
            "geometry_dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json,
            "semantic_analysis": semantic_json.get("input_text", ""),
        }
