from typing import Dict, Any, List
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine

from agents.ocr_agent import OCRAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.renderer_agent import RendererAgent

class Orchestrator:
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.geometry_agent = GeometryAgent()
        self.ocr_agent = OCRAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.renderer_agent = RendererAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()

    async def run(self, text: str, image_url: str = None, job_id: str = None) -> Dict[str, Any]:
        # 1. OCR if image provided
        input_text = text
        if image_url:
            input_text = await self.ocr_agent.process_url(image_url)

        feedback = None
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            # 2. Parse text to Semantic JSON (with feedback loop)
            semantic_json = await self.parser_agent.process(input_text, feedback=feedback)
            semantic_json["input_text"] = input_text
            
            # 3. Augment with Knowledge
            semantic_json = self.knowledge_agent.augment_semantic_data(semantic_json)
            
            # 4. Convert Semantic JSON to DSL
            # (Assuming Parser already outputs something close to DSL or we have a translator)
            # For brevity, let's say GeometryAgent handles the final refinement
            dsl_code = await self.geometry_agent.generate_dsl(semantic_json)
            
            # 5. Parse DSL to Solver Models
            points, constraints = self.dsl_parser.parse(dsl_code)
            
            # 6. Solve for coordinates
            coordinates = self.solver_engine.solve(points, constraints)
            
            if coordinates:
                break # Success!
            else:
                feedback = "Geometry solver failed to find a valid solution for the given constraints. Parallelism or lengths might be inconsistent."
                if attempt == max_retries:
                    return {"error": "Solver failed after multiple attempts.", "last_dsl": dsl_code}

        # 7. Hand over to Background Worker for Manim Rendering
        from worker.tasks import render_geometry_video
        
        result_payload = {
            "dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json
        }
        
        # Dispatch background task
        render_geometry_video.delay(job_id, result_payload)
        
        return {
            "status": "rendering_queued",
            "dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json
        }

class ParserAgent:
    """Mock Parser Agent for Phase 2 PoC"""
    async def process(self, text: str) -> Dict[str, Any]:
        # Simple Mock: Extracting entities from fixed triangle example
        return {
            "entities": ["A", "B", "C"],
            "type": "triangle",
            "values": {"AB": 5, "AC": 7, "angle_A": 60}
        }

class GeometryAgent:
    """Mock Geometry Agent for Phase 2 PoC"""
    async def generate_dsl(self, semantic_data: Dict[str, Any]) -> str:
        # Mocking DSL generation from semantic data
        v = semantic_data["values"]
        dsl = f"POINT(A)\nPOINT(B)\nPOINT(C)\nTRIANGLE(ABC)\n"
        dsl += f"LENGTH(AB, {v['AB']})\n"
        dsl += f"LENGTH(AC, {v['AC']})\n"
        dsl += f"ANGLE(A, {v['angle_A']}deg)"
        return dsl
