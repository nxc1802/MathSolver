import os
from supabase import create_client, Client
from typing import Dict, Any, List

class RendererAgent:
    """Renderer Agent integrated with Supabase Storage"""
    def __init__(self):
        self.supabase: Client = create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY")
        )
        self.bucket = os.environ.get("SUPABASE_BUCKET", "video")

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

    async def get_video_url(self, manim_script: str) -> str:
        # In a real setup, we would run Manim locally and then upload the file.
        # Since we can't run Manim here, we simulate the upload of a "local file".
        # Assume 'output.mp4' was generated.
        
        # Example of real upload logic (commented for stub):
        # with open('output.mp4', 'rb') as f:
        #     self.supabase.storage.from_(self.bucket).upload('result.mp4', f)
        
        # Return public URL from Supabase
        return f"{os.environ.get('SUPABASE_URL')}/storage/v1/object/public/{self.bucket}/demo_triangle.mp4"
