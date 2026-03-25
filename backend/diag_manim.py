import os
import subprocess

job_id = "test_diag"
script_file = f"{job_id}.py"
script_content = """from manim import *
class GeometryScene(Scene):
    def construct(self):
        self.add(Dot())
"""

with open(script_file, "w") as f:
    f.write(script_content)

print(f"Current Dir: {os.getcwd()}")
try:
    cmd = ["manim", "-ql", "--media_dir", ".", "-o", f"{job_id}.mp4", script_file, "GeometryScene"]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    print("\nListing all files in current directory recursively:")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".mp4"):
                print(os.path.join(root, file))
finally:
    if os.path.exists(script_file):
        os.remove(script_file)
