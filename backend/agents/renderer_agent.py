import os
import subprocess
import glob
import string
from typing import Dict, Any, List


class RendererAgent:
    """
    Renderer Agent — generates Manim scripts from geometry data.

    Drawing happens in phases:
      Phase 1: Main polygon (base shape with correct vertex order)
      Phase 2: Auxiliary points and segments (midpoints, derived segments)
      Phase 3: Labels for all points
    """

    def generate_manim_script(self, data: Dict[str, Any]) -> str:
        coords: Dict[str, List[float]] = data.get("coordinates", {})
        polygon_order: List[str] = data.get("polygon_order", [])
        circles_meta: List[Dict] = data.get("circles", [])
        drawing_phases: List[Dict] = data.get("drawing_phases", [])

        # ── Fallback: infer polygon_order from coords keys (alphabetical uppercase) ──
        if not polygon_order:
            base = sorted(
                [pid for pid in coords if pid in string.ascii_uppercase],
                key=lambda p: string.ascii_uppercase.index(p)
            )
            polygon_order = base

        # Separate base points from derived (multi-char or lowercase)
        base_ids = [pid for pid in polygon_order if pid in coords]
        derived_ids = [pid for pid in coords if pid not in polygon_order]

        lines = [
            "from manim import *",
            "",
            "class GeometryScene(MovingCameraScene):",
            "    def construct(self):",
        ]

        # ── Declare all dots and labels ───────────────────────────────────────
        for pid, pos in coords.items():
            x, y = round(pos[0], 4), round(pos[1], 4)
            lines.append(f"        p_{pid} = Dot(point=[{x}, {y}, 0], color=WHITE, radius=0.08)")
            lines.append(
                f"        l_{pid} = Text('{pid}', font_size=22, color=WHITE)"
                f".next_to(p_{pid}, UR, buff=0.15)"
            )

        # ── Circles ──────────────────────────────────────────────────────────
        for i, c in enumerate(circles_meta):
            center = c["center"]
            r = c["radius"]
            if center in coords:
                cx, cy = round(coords[center][0], 4), round(coords[center][1], 4)
                lines.append(
                    f"        circle_{i} = Circle(radius={r}, color=BLUE)"
                    f".move_to([{cx}, {cy}, 0])"
                )

        # ── Camera auto-fit group ─────────────────────────────────────────────
        all_dot_names = [f"p_{pid}" for pid in coords]
        all_names_str = ", ".join(all_dot_names)
        lines.append(f"        _all = VGroup({all_names_str})")
        lines.append("        self.camera.frame.set_width(max(_all.width * 2.0, 8))")
        lines.append("        self.camera.frame.move_to(_all)")
        lines.append("")

        # ── Phase 1: Base polygon ─────────────────────────────────────────────
        if len(base_ids) >= 3:
            pts_str = ", ".join([f"p_{pid}.get_center()" for pid in base_ids])
            lines.append(f"        poly = Polygon({pts_str}, color=BLUE, fill_color=BLUE, fill_opacity=0.15)")
            lines.append("        self.play(Create(poly), run_time=1.5)")
        elif len(base_ids) == 2:
            p1, p2 = base_ids
            lines.append(f"        base_line = Line(p_{p1}.get_center(), p_{p2}.get_center(), color=BLUE)")
            lines.append("        self.play(Create(base_line), run_time=1.0)")

        # Draw base points
        if base_ids:
            base_dots_str = ", ".join([f"p_{pid}" for pid in base_ids])
            lines.append(f"        self.play(FadeIn(VGroup({base_dots_str})), run_time=0.5)")
        lines.append("        self.wait(0.5)")

        # ── Phase 2: Auxiliary points and segments ────────────────────────────
        if derived_ids:
            derived_dots_str = ", ".join([f"p_{pid}" for pid in derived_ids])
            lines.append(f"        self.play(FadeIn(VGroup({derived_dots_str})), run_time=0.8)")

        # Segments from drawing_phases
        segment_lines = []
        for phase in drawing_phases:
            if phase.get("phase") == 2:
                for seg in phase.get("segments", []):
                    if len(seg) == 2 and seg[0] in coords and seg[1] in coords:
                        p1, p2 = seg[0], seg[1]
                        seg_var = f"seg_{p1}_{p2}"
                        lines.append(
                            f"        {seg_var} = Line(p_{p1}.get_center(), p_{p2}.get_center(),"
                            f" color=YELLOW)"
                        )
                        segment_lines.append(seg_var)

        if segment_lines:
            segs_str = ", ".join([f"Create({sv})" for sv in segment_lines])
            lines.append(f"        self.play({segs_str}, run_time=1.2)")

        if derived_ids or segment_lines:
            lines.append("        self.wait(0.5)")

        # ── Phase 3: All labels ───────────────────────────────────────────────
        all_labels_str = ", ".join([f"l_{pid}" for pid in coords])
        lines.append(f"        self.play(FadeIn(VGroup({all_labels_str})), run_time=0.8)")

        # ── Circles phase ─────────────────────────────────────────────────────
        for i in range(len(circles_meta)):
            lines.append(f"        self.play(Create(circle_{i}), run_time=1.5)")

        lines.append("        self.wait(2)")

        return "\n".join(lines)

    def run_manim(self, script_content: str, job_id: str) -> str:
        import subprocess
        import os
        import glob

        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)

        try:
            print(f"Running Manim for job {job_id}...")
            result = subprocess.run(
                ["manim", "-ql", "--media_dir", ".", "-o", f"{job_id}.mp4", script_file, "GeometryScene"],
                capture_output=True,
                text=True,
            )
            print(f"Manim STDOUT: {result.stdout}")
            print(f"Manim STDERR: {result.stderr}")

            for pattern in [f"**/videos/**/{job_id}.mp4", f"**/{job_id}*.mp4"]:
                found = glob.glob(pattern, recursive=True)
                if found:
                    print(f"Manim Success: Found {found[0]}")
                    return found[0]

            print(f"Manim file not found for job {job_id}")
            return ""
        except Exception as e:
            print(f"Manim Execution Error: {e}")
            return ""
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
