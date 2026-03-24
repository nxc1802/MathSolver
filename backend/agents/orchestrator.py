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

    async def run(self, text: str, image_url: str = None) -> Dict[str, Any]:
        # 1. OCR if image provided
        input_text = text
        if image_url:
            input_text = await self.ocr_agent.process_url(image_url)

        # 2. Parse text to Semantic JSON
        semantic_json = await self.parser_agent.process(input_text)
        semantic_json["input_text"] = input_text
        
        # 3. Augment with Knowledge
        semantic_json = self.knowledge_agent.augment_semantic_data(semantic_json)
        
        # 4. Convert Semantic JSON to DSL
        dsl_code = await self.geometry_agent.generate_dsl(semantic_json)
        
        # 5. Parse DSL to Solver Models
        points, constraints = self.dsl_parser.parse(dsl_code)
        
        # 6. Solve for coordinates
        coordinates = self.solver_engine.solve(points, constraints)
        
        # 6. Generate Animation Script & Mock Video URL
        result_data = {
            "dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json
        }
        manim_script = self.renderer_agent.generate_manim_script(result_data)
        video_url = await self.renderer_agent.get_video_url(manim_script)
        
        return {
            "dsl": dsl_code,
            "coordinates": coordinates,
            "semantic": semantic_json,
            "manim_script": manim_script,
            "video_url": video_url
        }

import os
import json
from openai import OpenAI
from typing import Dict, Any, List

class ParserAgent:
    """Real Parser Agent using MegaLLM"""
    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("MEGALLM_BASE_URL"),
            api_key=os.environ.get("MEGALLM_API_KEY")
        )

    async def process(self, text: str) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a Geometry Parser. Parse the user problem into a JSON with 'entities' (list of points), 'type' (shape type), and 'values' (dictionary of lengths and angles). Example: {'entities':['A','B','C'], 'type':'triangle', 'values':{'AB':5, 'AC':7, 'angle_A':60}}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

class GeometryAgent:
    """Real Geometry Agent using MegaLLM to generate DSL"""
    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("MEGALLM_BASE_URL"),
            api_key=os.environ.get("MEGALLM_API_KEY")
        )

    async def generate_dsl(self, semantic_data: Dict[str, Any]) -> str:
        response = self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a Geometry DSL Generator. Convert the semantic JSON into Geometry DSL code. Valid keywords: POINT(id), LINE(p1,p2), TRIANGLE(p1p2p3), LENGTH(p1p2, val), ANGLE(v, val_deg)."},
                {"role": "user", "content": json.dumps(semantic_data)}
            ]
        )
        return response.choices[0].message.content.strip()
