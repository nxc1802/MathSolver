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
            script += f"        l_{pid} = Text('{pid}', font_size=24).next_to(p_{pid}, UR, buff=0.2)\n"
            script += f"        self.add(p_{pid}, l_{pid})\n"
            pt_objs.append(f"p_{pid}")
        
        # Draw polygons (e.g., triangle A-B-C)
        if len(pt_objs) >= 3:
            pts_str = ", ".join([f"{p}.get_center()" for p in pt_objs])
            script += f"        poly = Polygon({pts_str}, color=BLUE, fill_opacity=0.3)\n"
            script += "        self.play(Create(poly), run_time=2)\n"
            script += "        self.wait(1)\n"

        return script

    def run_manim(self, script_content: str, job_id: str) -> Dict[str, str]:
        import subprocess
        import os
        import glob
        
        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)
        
        paths = {"video": "", "image": ""}
        
        try:
            print(f"Running Manim for job {job_id}...")
            # Run for Video
            result_v = subprocess.run(
                ["manim", "-ql", "--media_dir", ".", "-o", f"{job_id}.mp4", script_file, "GeometryScene"],
                capture_output=True, text=True
            )
            print(f"Manim Video Code: {result_v.returncode}")

            # Run for Static Image (-s saves the last frame)
            result_i = subprocess.run(
                ["manim", "-ql", "-s", "--media_dir", ".", "-o", f"{job_id}.png", script_file, "GeometryScene"],
                capture_output=True, text=True
            )
            print(f"Manim Image Code: {result_i.returncode}")

            # Find video
            found_v = glob.glob(f"**/videos/**/{job_id}.mp4", recursive=True)
            if found_v: paths["video"] = found_v[0]

            # Find image (Manim -s usually puts it in images/...)
            found_i = glob.glob(f"**/images/**/{job_id}.png", recursive=True)
            if not found_i: # Fallback search for any png with job_id
                found_i = glob.glob(f"**/{job_id}*.png", recursive=True)
            if found_i: paths["image"] = found_i[0]

            print(f"Manim Paths: {paths}")
            return paths
            
        except Exception as e:
            print(f"Manim Execution Error: {e}")
            return paths
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
