import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        from agents.ocr_agent import OCRAgent
        from agents.knowledge_agent import KnowledgeAgent
        from agents.renderer_agent import RendererAgent
        from agents.parser_agent import ParserAgent
        from agents.geometry_agent import GeometryAgent
        from solver.dsl_parser import DSLParser
        from solver.engine import GeometryEngine

        self.parser_agent = ParserAgent()
        self.geometry_agent = GeometryAgent()
        self.ocr_agent = OCRAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.renderer_agent = RendererAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()

    async def run(self, text: str, image_url: str = None, job_id: str = None, status_callback=None, request_video: bool = False) -> Dict[str, Any]:
        logger.info(f"====== [Orchestrator] Job {job_id} STARTED ======")
        logger.info(f"[Orchestrator] Input: text_len={len(text)}, image_url={image_url}, request_video={request_video}")

        if status_callback:
            await status_callback("processing")

        # --- Step 1: OCR ---
        input_text = text
        if image_url:
            logger.info("[Orchestrator] Step 1: Running OCRAgent on image URL...")
            input_text = await self.ocr_agent.process_url(image_url)
            logger.info(f"[Orchestrator] Step 1 DONE: OCR extracted {len(input_text)} chars.")
        else:
            logger.info("[Orchestrator] Step 1: Skipped (no image URL, using text input directly).")

        feedback = None
        MAX_RETRIES = 2

        for attempt in range(MAX_RETRIES + 1):
            logger.info(f"[Orchestrator] ---- Attempt {attempt + 1}/{MAX_RETRIES + 1} ----")
            if status_callback:
                await status_callback("solving")

            # --- Step 2: Parse ---
            logger.info("[Orchestrator] Step 2: Running ParserAgent...")
            semantic_json = await self.parser_agent.process(input_text, feedback=feedback)
            semantic_json["input_text"] = input_text
            logger.info(f"[Orchestrator] Step 2 DONE: Entities={semantic_json.get('entities')}, Values={semantic_json.get('values')}")

            # --- Step 3: Knowledge Augmentation ---
            logger.info("[Orchestrator] Step 3: Running KnowledgeAgent...")
            semantic_json = self.knowledge_agent.augment_semantic_data(semantic_json)
            logger.info("[Orchestrator] Step 3 DONE.")

            # --- Step 4: DSL Generation ---
            logger.info("[Orchestrator] Step 4: Running GeometryAgent (DSL generation)...")
            dsl_code = await self.geometry_agent.generate_dsl(semantic_json)
            logger.info("[Orchestrator] Step 4 DONE.")

            # --- Step 5: DSL Parsing ---
            logger.info("[Orchestrator] Step 5: Parsing DSL with DSLParser...")
            points, constraints = self.dsl_parser.parse(dsl_code)
            logger.info(f"[Orchestrator] Step 5 DONE: {len(points)} points, {len(constraints)} constraints.")

            # --- Step 6: Solve ---
            logger.info("[Orchestrator] Step 6: Running GeometryEngine (Constraint Solver)...")
            coordinates = self.solver_engine.solve(points, constraints)

            if coordinates:
                logger.info(f"[Orchestrator] Step 6 DONE: Solved successfully. Coordinates: {coordinates}")
                break
            else:
                feedback = "Geometry solver failed to find a valid solution for the given constraints. Parallelism or lengths might be inconsistent."
                logger.warning(f"[Orchestrator] Step 6 FAILED on attempt {attempt + 1}. Feedback: {feedback}")
                if attempt == MAX_RETRIES:
                    logger.error(f"[Orchestrator] All {MAX_RETRIES + 1} attempts failed. Returning error for job {job_id}.")
                    return {"error": "Solver failed after multiple attempts.", "last_dsl": dsl_code}

        # --- Step 7: Rendering (optional) ---
        status = "success"
        if request_video:
            logger.info(f"🎬 [Orchestrator] Step 7: Dispatching video render task to Celery for Job {job_id}...")
            try:
                from worker.tasks import render_geometry_video
                from worker.celery_app import BROKER_URL
                logger.debug(f"[Orchestrator] Using Celery Broker: {BROKER_URL[:20]}...")
                
                result_payload = {
                    "geometry_dsl": dsl_code,
                    "coordinates": coordinates,
                    "semantic": semantic_json,
                    "semantic_analysis": semantic_json.get("input_text", "")
                }
                task = render_geometry_video.delay(job_id, result_payload)
                status = "rendering_queued"
                logger.info(f"✅ [Orchestrator] Step 7 DONE: Task {task.id} queued successfully.")
            except Exception as e:
                logger.error(f"❌ [Orchestrator] Step 7 FAILED to queue task: {str(e)}")
                # Don't fail the whole job, but revert status
                status = "success" 
        else:
            logger.info("[Orchestrator] Step 7: Video not requested. Skipping Manim render.")

        logger.info(f"====== [Orchestrator] Job {job_id} FINISHED with status='{status}' ======")

        return {
            "status": status,
            "geometry_dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json,
            "semantic_analysis": semantic_json.get("input_text", "")
        }
