import os
import re
import subprocess
import glob
import string
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _sanitize_var(pid: str) -> str:
    """Convert point ID like A' or A_1 to valid Python identifier."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(pid))
    if not sanitized or sanitized[0].isdigit():
        sanitized = f"pt_{sanitized}"
    return sanitized


class RendererAgent:
    """
    Renderer — generates Manim scripts from geometry data.

    Drawing happens in phases:
      Phase 1: Main polygon / 3D base shape
      Phase 2: Auxiliary points, 3D faces and segments
      Phase 3: Labels and 3D solids
    """

    def generate_manim_script(self, data: Dict[str, Any]) -> str:
        coords: Dict[str, List[float]] = data.get("coordinates", {})
        polygon_order: List[str] = data.get("polygon_order", [])
        circles_meta: List[Dict] = data.get("circles", [])
        solids_meta: List[Dict] = data.get("solids", [])
        faces_meta: List[List[str]] = data.get("faces", [])
        lines_meta: List[List[str]] = data.get("lines", [])
        rays_meta: List[List[str]] = data.get("rays", [])
        drawing_phases: List[Dict] = data.get("drawing_phases", [])
        semantic: Dict[str, Any] = data.get("semantic", {})
        shape_type = semantic.get("type", "").lower()

        # ── Detect 3D Context ────────────────────────────────────────────────
        is_3d = False
        for pos in coords.values():
            if len(pos) >= 3 and abs(pos[2]) > 0.001:
                is_3d = True
                break
        if shape_type in ["pyramid", "prism", "sphere", "cube", "cuboid", "tetrahedron", "cone", "cylinder", "frustum", "regular_pyramid", "regular_tetrahedron", "right_prism"] or solids_meta or data.get("is_3d"):
            is_3d = True

        # Fallback: infer polygon_order from coords keys
        if not polygon_order:
            base = sorted(
                [pid for pid in coords if pid in string.ascii_uppercase],
                key=lambda p: string.ascii_uppercase.index(p)
            )
            polygon_order = base if base else list(coords.keys())[:4]

        base_ids = [pid for pid in polygon_order if pid in coords]
        derived_ids = [pid for pid in coords if pid not in polygon_order]

        scene_base = "ThreeDScene" if is_3d else "MovingCameraScene"
        lines = [
            "from manim import *",
            "",
            f"class GeometryScene({scene_base}):",
            "    def construct(self):",
        ]

        if is_3d:
            lines.append("        # 3D Setup")
            lines.append("        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)")
            lines.append("        axes = ThreeDAxes(axis_config={'stroke_width': 1})")
            lines.append("        axes.set_opacity(0.3)")
            lines.append("        self.add(axes)")
            lines.append("        self.begin_ambient_camera_rotation(rate=0.1)")
            lines.append("")

        # ── Declare all dots and labels ───────────────────────────────────────
        for pid, pos in coords.items():
            x, y, z = 0, 0, 0
            if len(pos) >= 1: x = round(pos[0], 4)
            if len(pos) >= 2: y = round(pos[1], 4)
            if len(pos) >= 3: z = round(pos[2], 4)

            v_name = _sanitize_var(pid)
            dot_class = "Dot3D" if is_3d else "Dot"
            lines.append(f"        p_{v_name} = {dot_class}(point=[{x}, {y}, {z}], color=WHITE, radius=0.08)")

            if is_3d:
                lines.append(
                    f"        l_{v_name} = Text('{pid}', font_size=20, color=WHITE)"
                    f".move_to(p_{v_name}.get_center() + [0.2, 0.2, 0.2])"
                )
                lines.append(f"        self.add_fixed_orientation_mobjects(l_{v_name})")
            else:
                lines.append(
                    f"        l_{v_name} = Text('{pid}', font_size=22, color=WHITE)"
                    f".next_to(p_{v_name}, UR, buff=0.15)"
                )

        # ── 3D Shape Special: Translucent Faces ───────────────────────────────
        if is_3d and faces_meta:
            lines.append("        # 3D Faces")
            for idx, face in enumerate(faces_meta):
                if len(face) >= 3 and all(p in coords for p in face):
                    face_pts = ", ".join([f"p_{_sanitize_var(p)}.get_center()" for p in face])
                    f_var = f"face_{idx}"
                    lines.append(f"        {f_var} = Polygon({face_pts}, color=BLUE, stroke_width=1, fill_color=BLUE, fill_opacity=0.08)")
                    lines.append(f"        self.play(Create({f_var}), run_time=0.4)")

        # ── Circles ──────────────────────────────────────────────────────────
        for i, c in enumerate(circles_meta):
            center = c["center"]
            r = c["radius"]
            if center in coords:
                cx, cy, cz = 0, 0, 0
                pos = coords[center]
                if len(pos) >= 1: cx = round(pos[0], 4)
                if len(pos) >= 2: cy = round(pos[1], 4)
                if len(pos) >= 3: cz = round(pos[2], 4)
                lines.append(
                    f"        circle_{i} = Circle(radius={r}, color=BLUE)"
                    f".move_to([{cx}, {cy}, {cz}])"
                )

        # ── Infinite Lines & Rays ────────────────────────────────────────────
        for i, (p1, p2) in enumerate(lines_meta):
            if p1 in coords and p2 in coords:
                v1, v2 = _sanitize_var(p1), _sanitize_var(p2)
                lines.append(
                    f"        line_ext_{i} = Line(p_{v1}.get_center(), p_{v2}.get_center(), color=GRAY_D, stroke_width=2)"
                    f".scale(20)"
                )

        for i, (p1, p2) in enumerate(rays_meta):
            if p1 in coords and p2 in coords:
                v1, v2 = _sanitize_var(p1), _sanitize_var(p2)
                lines.append(
                    f"        ray_{i} = Line(p_{v1}.get_center(), p_{v1}.get_center() + 15 * (p_{v2}.get_center() - p_{v1}.get_center()),"
                    f" color=GRAY_C, stroke_width=2)"
                )

        # ── Camera auto-fit group (Only for 2D) ──────────────────────────────
        if not is_3d:
            all_dot_names = [f"p_{_sanitize_var(pid)}" for pid in coords]
            all_names_str = ", ".join(all_dot_names)
            lines.append(f"        _all = VGroup({all_names_str})")
            lines.append("        self.camera.frame.set_width(max(_all.width * 2.0, 8))")
            lines.append("        self.camera.frame.move_to(_all)")
        lines.append("")

        # ── Phase 1: Base polygon ─────────────────────────────────────────────
        if len(base_ids) >= 3 and not faces_meta:
            pts_str = ", ".join([f"p_{_sanitize_var(pid)}.get_center()" for pid in base_ids])
            lines.append(f"        poly = Polygon({pts_str}, color=BLUE, fill_color=BLUE, fill_opacity=0.15)")
            lines.append("        self.play(Create(poly), run_time=1.5)")
        elif len(base_ids) == 2:
            p1, p2 = base_ids
            v1, v2 = _sanitize_var(p1), _sanitize_var(p2)
            lines.append(f"        base_line = Line(p_{v1}.get_center(), p_{v2}.get_center(), color=BLUE)")
            lines.append("        self.play(Create(base_line), run_time=1.0)")

        # Draw base points
        if base_ids:
            base_dots_str = ", ".join([f"p_{_sanitize_var(pid)}" for pid in base_ids])
            lines.append(f"        self.play(FadeIn(VGroup({base_dots_str})), run_time=0.5)")
        lines.append("        self.wait(0.5)")

        # ── Phase 2: Auxiliary points and segments ────────────────────────────
        if derived_ids:
            derived_dots_str = ", ".join([f"p_{_sanitize_var(pid)}" for pid in derived_ids])
            lines.append(f"        self.play(FadeIn(VGroup({derived_dots_str})), run_time=0.8)")

        # Segments from drawing_phases
        segment_lines = []
        for phase in drawing_phases:
            for seg in phase.get("segments", []):
                if len(seg) == 2 and seg[0] in coords and seg[1] in coords:
                    p1, p2 = seg[0], seg[1]
                    v1, v2 = _sanitize_var(p1), _sanitize_var(p2)
                    seg_var = f"seg_{v1}_{v2}"
                    if seg_var not in segment_lines:
                        lines.append(
                            f"        {seg_var} = Line(p_{v1}.get_center(), p_{v2}.get_center(),"
                            f" color={'BLUE' if phase.get('phase') == 1 else 'YELLOW'})"
                        )
                        segment_lines.append(seg_var)

        if segment_lines:
            segs_str = ", ".join([f"Create({sv})" for sv in segment_lines[:15]]) # limit batch for smooth animation
            lines.append(f"        self.play({segs_str}, run_time=1.5)")
            if len(segment_lines) > 15:
                segs_str_2 = ", ".join([f"Create({sv})" for sv in segment_lines[15:]])
                lines.append(f"        self.play({segs_str_2}, run_time=1.0)")

        if derived_ids or segment_lines:
            lines.append("        self.wait(0.5)")

        # ── Phase 3: All labels ───────────────────────────────────────────────
        all_labels_str = ", ".join([f"l_{_sanitize_var(pid)}" for pid in coords])
        lines.append(f"        self.play(FadeIn(VGroup({all_labels_str})), run_time=0.8)")

        # ── Circles phase ─────────────────────────────────────────────────────
        for i in range(len(circles_meta)):
            lines.append(f"        self.play(Create(circle_{i}), run_time=1.5)")

        # ── Lines & Rays phase ────────────────────────────────────────────────
        if lines_meta or rays_meta:
            lr_anims = []
            for i in range(len(lines_meta)):
                lr_anims.append(f"Create(line_ext_{i})")
            for i in range(len(rays_meta)):
                lr_anims.append(f"Create(ray_{i})")
            lines.append(f"        self.play({', '.join(lr_anims)}, run_time=1.5)")

        lines.append("        self.wait(2)")

        return "\n".join(lines)

    def run_manim(self, script_content: str, job_id: str) -> str:
        script_file = f"{job_id}.py"
        with open(script_file, "w") as f:
            f.write(script_content)

        try:
            if os.getenv("MOCK_VIDEO") == "true":
                logger.info(f"MOCK_VIDEO is true. Skipping Manim for job {job_id}")
                dummy_path = f"videos/{job_id}.mp4"
                os.makedirs("videos", exist_ok=True)
                with open(dummy_path, "wb") as f:
                    f.write(b"dummy video content")
                return dummy_path

            manim_exe = "manim"
            venv_manim = os.path.join(os.getcwd(), "venv", "bin", "manim")
            if os.path.exists(venv_manim):
                manim_exe = venv_manim

            custom_env = os.environ.copy()
            brew_path = "/opt/homebrew/bin:/usr/local/bin"
            custom_env["PATH"] = f"{brew_path}:{custom_env.get('PATH', '')}"

            logger.info(f"Running {manim_exe} for job {job_id}...")
            result = subprocess.run(
                [manim_exe, "-ql", "--media_dir", ".", "-o", f"{job_id}.mp4", script_file, "GeometryScene"],
                capture_output=True,
                text=True,
                env=custom_env,
            )
            logger.info(f"Manim STDOUT: {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Manim STDERR: {result.stderr}")

            for pattern in [f"**/videos/**/{job_id}.mp4", f"**/{job_id}*.mp4"]:
                found = glob.glob(pattern, recursive=True)
                if found:
                    logger.info(f"Manim Success: Found {found[0]}")
                    return found[0]

            logger.error(f"Manim file not found for job {job_id}. Return code: {result.returncode}")
            return ""
        except Exception as e:
            logger.exception(f"Manim Execution Error: {e}")
            return ""
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
