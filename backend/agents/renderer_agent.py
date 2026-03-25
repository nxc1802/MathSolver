from typing import Dict, Any, List

class RendererAgent:
    """Renderer Agent for Phase 4.
    Generates Manim Python scripts based on coordinates and geometry types.
    """
    def generate_manim_script(self, data: Dict[str, Any]) -> str:
        coords = data.get("coordinates", {})
        
        script = "from manim import *\n\n"
        script += "class GeometryScene(Scene):\n"
        script += "    def construct(self):\n"
        
        # Draw all points and labels
        pt_objs = []
        for pid, pos in coords.items():
            script += f"        p_{pid} = Dot(point=[{pos[0]}, {pos[1]}, 0], color=WHITE)\n"
            script += f"        l_{pid} = MathTex('{pid}').next_to(p_{pid}, UR, buff=0.2)\n"
            script += f"        self.add(p_{pid}, l_{pid})\n"
            pt_objs.append(f"p_{pid}")
        
        # Draw polygons (e.g., triangle A-B-C)
        if len(pt_objs) >= 3:
            pts_str = ", ".join([f"{p}.get_center()" for p in pt_objs])
            script += f"        poly = Polygon({pts_str}, color=BLUE, fill_opacity=0.3)\n"
            script += "        self.play(Create(poly), run_time=2)\n"
            script += "        self.wait(1)\n"

        return script

    def run_manim(self, script_content: str, job_id: str) -> str:
        import subprocess
        import os
        
        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)
        
        try:
            # -qm for medium quality, -o for output filename
            subprocess.run(["manim", "-qm", "-o", f"{job_id}.mp4", script_file, "GeometryScene"], check=True)
            
            # Manim output usually goes to media/videos/{job_id}/720p30/{job_id}.mp4
            video_path = f"media/videos/{job_id}/720p30/{job_id}.mp4"
            return video_path
        except Exception as e:
            print(f"Manim Execution Error: {e}")
            return ""
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
