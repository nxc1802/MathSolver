from typing import Dict, Any, List

class RendererAgent:
    """Renderer Agent for Phase 4.
    Generates Manim Python scripts based on coordinates and geometry types.
    """
    def generate_manim_script(self, data: Dict[str, Any]) -> str:
        coords = data.get("coordinates", {})
        
        script = "from manim import *\n\n"
        script += "class GeometryScene(MovingCameraScene):\n"
        script += "    def construct(self):\n"
        
        # Draw all points and labels
        pt_objs = []
        labels = []
        for pid, pos in coords.items():
            script += f"        p_{pid} = Dot(point=[{pos[0]}, {pos[1]}, 0], color=WHITE)\n"
            script += f"        l_{pid} = Text('{pid}', font='Arial', font_size=24).next_to(p_{pid}, UR, buff=0.2)\n"
            pt_objs.append(f"p_{pid}")
            labels.append(f"l_{pid}")
        
        # Draw polygons
        poly_objs = []
        if len(pt_objs) >= 3:
            pts_str = ", ".join([f"{p}.get_center()" for p in pt_objs])
            script += f"        poly = Polygon({pts_str}, color=BLUE, fill_opacity=0.3)\n"
            poly_objs.append("poly")

        # Create a group for all objects to center and scale
        all_mobs_str = ", ".join(pt_objs + labels + poly_objs)
        script += f"        all_mobs = VGroup({all_mobs_str})\n"
        script += "        all_mobs.center()\n"
        script += "        # Auto-scale camera to fit the group with some buffer\n"
        script += "        self.camera.frame.set_width(max(all_mobs.width * 1.5, 8))\n"
        script += "        self.camera.frame.move_to(all_mobs)\n\n"

        # Animations
        script += f"        self.add({all_mobs_str})\n"
        if poly_objs:
            script += "        self.play(Create(poly), run_time=2)\n"
        script += "        self.wait(2)\n"

        return script

    def run_manim(self, script_content: str, job_id: str) -> str:
        import subprocess
        import os
        import glob
        
        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)
        
        try:
            print(f"Running Manim for job {job_id}...")
            # Use -ql for faster testing locally, can switch back to -qm for prod
            result = subprocess.run(
                ["manim", "-ql", "--media_dir", ".", "-o", f"{job_id}.mp4", script_file, "GeometryScene"],
                capture_output=True,
                text=True
            )
            
            print(f"Manim STDOUT: {result.stdout}")
            print(f"Manim STDERR: {result.stderr}")

            # Recursive search for the created .mp4 file
            search_pattern = f"**/videos/**/{job_id}.mp4"
            found_files = glob.glob(search_pattern, recursive=True)
            
            if found_files:
                video_path = found_files[0]
                print(f"Manim Success: Found {video_path}")
                return video_path
            else:
                # Fallback: search for any .mp4 with job_id in the name
                search_pattern_fallback = f"**/{job_id}*.mp4"
                found_files_fallback = glob.glob(search_pattern_fallback, recursive=True)
                if found_files_fallback:
                    video_path = found_files_fallback[0]
                    print(f"Manim Success (Fallback): Found {video_path}")
                    return video_path
                
                print(f"Manim file could not be found for job {job_id}")
                return ""
        except Exception as e:
            print(f"Manim Execution Error: {e}")
            return ""
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
