from typing import Dict, Any, List

class RendererAgent:
    """Renderer Agent for Phase 4.
    Generates Manim Python scripts based on coordinates and geometry types.
    """
    def generate_manim_script(self, data: Dict[str, Any]) -> str:
        coords = data.get("coordinates", {})
        semantic = data.get("semantic", {})
        
        script = "from manim import *\n\n"
        script += "class GeometryScene(Scene):\n"
        script += "    def construct(self):\n"
        
        # 1. Create Points
        for pid, pos in coords.items():
            # pos is [x, y], Manim uses [x, y, z]
            script += f"        p_{pid} = Dot(point=[{pos[0]/2}, {pos[1]/2}, 0])\n"
            script += f"        l_{pid} = Text('{pid}').next_to(p_{pid}, UR)\n"
            script += f"        self.add(p_{pid}, l_{pid})\n"
            script += f"        self.play(Create(p_{pid}), Write(l_{pid}))\n"
            
        # 2. Create Lines for Triangle/Polygon
        if semantic.get("type") in ["triangle", "triangle_equilateral"]:
            script += "        line_ab = Line(p_A.get_center(), p_B.get_center())\n"
            script += "        line_bc = Line(p_B.get_center(), p_C.get_center())\n"
            script += "        line_ca = Line(p_C.get_center(), p_A.get_center())\n"
            script += "        self.play(Create(line_ab), Create(line_bc), Create(line_ca))\n"

        return script

    def run_manim(self, script_content: str, job_id: str) -> str:
        import subprocess
        import os
        
        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run Manim command
        try:
            subprocess.run(["manim", "-ql", script_file, "GeometryScene"], check=True)
            # Manim outputs to media/videos/{script_file}/480p15/GeometryScene.mp4 roughly
            video_path = f"media/videos/{job_id}/480p15/GeometryScene.mp4"
            return video_path
        except Exception as e:
            print(f"Manim Execution Error: {e}")
            return ""

    async def get_video_url(self, manim_script: str) -> str:
        # Mock URL for Phase 4 PoC
        return "https://storage.googleapis.com/math-solver-v3/videos/demo_triangle.mp4"
