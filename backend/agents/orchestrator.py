from typing import Dict, Any, List
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine

class Orchestrator:
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.geometry_agent = GeometryAgent()
        self.solver_engine = GeometryEngine()
        self.dsl_parser = DSLParser()

    async def run(self, text: str) -> Dict[str, Any]:
        # 1. Parse text to Semantic JSON
        semantic_json = await self.parser_agent.process(text)
        
        # 2. Convert Semantic JSON to DSL
        dsl_code = await self.geometry_agent.generate_dsl(semantic_json)
        
        # 3. Parse DSL to Solver Models
        points, constraints = self.dsl_parser.parse(dsl_code)
        
        # 4. Solve for coordinates
        coordinates = self.solver_engine.solve(points, constraints)
        
        return {
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
