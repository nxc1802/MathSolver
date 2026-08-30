import re
import logging
from typing import List, Tuple, Dict, Any
from .models import Point, Constraint

logger = logging.getLogger(__name__)


def _parse_point_tokens(s: str) -> List[str]:
    """
    Parse a string of point names into a list of strings.
    Handles:
    - 'A, B, C' -> ['A', 'B', 'C']
    - 'ABCD' -> ['A', 'B', 'C', 'D']
    - 'A1B1C1D1' -> ['A1', 'B1', 'C1', 'D1']
    - "A'B'C'D'" -> ["A'", "B'", "C'", "D'"]
    - 'A_1, B_1' -> ['A_1', 'B_1']
    """
    s = s.strip()
    if not s:
        return []
    if ',' in s:
        return [p.strip() for p in s.split(',') if p.strip()]
    tokens = re.findall(r"[A-Za-z][0-9_']*", s)
    return tokens if tokens else [s]


def _add_poly_segments(pts: List[str], target_segments: List[List[str]], constraints: List[Constraint]):
    """Add cyclic segments for a polygon (e.g. A-B, B-C, C-D, D-A)."""
    if len(pts) < 2:
        return
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)] if len(pts) > 2 else pts[1]
        if [p1, p2] not in target_segments and [p2, p1] not in target_segments:
            target_segments.append([p1, p2])
            constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
        if len(pts) == 2:
            break


class DSLParser:
    def parse(self, text: str) -> Tuple[List[Point], List[Constraint], bool]:
        """Parse DSL text into points and constraints. Stateless per call."""
        points: Dict[str, Point] = {}
        explicit_point_ids: List[str] = []
        constraints: List[Constraint] = []
        polygon_order: List[str] = []
        circles: List[Dict[str, Any]] = []
        solids: List[Dict[str, Any]] = []
        segments: List[List[str]] = []
        lines_ext: List[List[str]] = []
        rays: List[List[str]] = []
        is_3d = False

        logger.info("==[DSLParser] Parsing DSL input (v5.2)==")
        logger.debug(f"[DSLParser] Raw DSL:\n{text}")

        def ensure_point(pid: str, x: float = None, y: float = None, z: float = None) -> Point:
            if pid not in points:
                points[pid] = Point(id=pid, x=x, y=y, z=z)
            else:
                if x is not None: points[pid].x = x
                if y is not None: points[pid].y = y
                if z is not None: points[pid].z = z
            return points[pid]

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue

            # POINT(A) or POINT(A, 0, 0, 5) or POINT(A1, 10, 0, 0)
            m = re.match(r'POINT\(([^,)]+)(?:,\s*([\d\.-]+),\s*([\d\.-]+)(?:,\s*([\d\.-]+))?)?\)', line)
            if m:
                name = m.group(1).strip()
                x = float(m.group(2)) if m.group(2) else None
                y = float(m.group(3)) if m.group(3) else None
                z = float(m.group(4)) if m.group(4) else None
                if z is not None and abs(z) > 1e-9:
                    is_3d = True
                ensure_point(name, x, y, z)
                if name not in explicit_point_ids:
                    explicit_point_ids.append(name)
                logger.debug(f"[DSLParser]   + POINT: {name} ({x}, {y}, {z})")
                continue

            # LENGTH(AB, 5) or LENGTH(A, B, 5)
            m = re.match(r'LENGTH\(([^,]+),\s*(?:([^,]+),\s*)?([\d\.]+)\)', line)
            if m:
                if m.group(2):
                    p1, p2, val = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
                    pts = [p1, p2]
                else:
                    target, val = m.group(1).strip(), float(m.group(3))
                    pts = _parse_point_tokens(target)
                if len(pts) >= 2:
                    ensure_point(pts[0])
                    ensure_point(pts[1])
                    constraints.append(Constraint(type='length', targets=pts[:2], value=val))
                    logger.debug(f"[DSLParser]   + LENGTH: {pts[:2]} = {val}")
                continue

            # ANGLE(A, 90) or ANGLE(A, B, C, 90) or ANGLE(ABC, 90deg)
            m = re.match(r'ANGLE\((.+)\)', line)
            if m:
                raw_args = [a.strip() for a in m.group(1).split(',')]
                if len(raw_args) >= 2:
                    val_str = raw_args[-1].replace('deg', '').strip()
                    try:
                        val = float(val_str)
                        target_args = raw_args[:-1]
                        if len(target_args) == 1:
                            pts = _parse_point_tokens(target_args[0])
                        else:
                            pts = target_args
                        for p in pts: ensure_point(p)
                        constraints.append(Constraint(type='angle', targets=pts, value=val))
                        logger.debug(f"[DSLParser]   + ANGLE: vertex/targets={pts}, degrees={val}")
                    except ValueError:
                        pass
                continue

            # PERPENDICULAR_PLANE(SO, ABCD) or LINE_PERP_PLANE(SO, ABC)
            m = re.match(r'(?:PERPENDICULAR_PLANE|LINE_PERP_PLANE)\(([^,]+),\s*([^)]+)\)', line)
            if m:
                is_3d = True
                line_pts = _parse_point_tokens(m.group(1))
                plane_pts = _parse_point_tokens(m.group(2))
                for p in line_pts + plane_pts: ensure_point(p)
                constraints.append(Constraint(type='perp_plane', targets=line_pts[:2] + plane_pts, value=0))
                logger.debug(f"[DSLParser]   + PERPENDICULAR_PLANE: line={line_pts[:2]} _|_ plane={plane_pts}")
                continue

            # COPLANAR(A, B, C, D) or COPLANAR(ABCD)
            m = re.match(r'COPLANAR\(([^)]+)\)', line)
            if m:
                is_3d = True
                pts = _parse_point_tokens(m.group(1))
                for p in pts: ensure_point(p)
                if len(pts) >= 4:
                    constraints.append(Constraint(type='coplanar', targets=pts, value=0))
                    logger.debug(f"[DSLParser]   + COPLANAR: {pts}")
                continue

            # POINT_ON_PLANE(P, ABC) or POINT_ON_PLANE(P, A, B, C)
            m = re.match(r'POINT_ON_PLANE\(([^,]+),\s*([^)]+)\)', line)
            if m:
                is_3d = True
                p_target = m.group(1).strip()
                plane_pts = _parse_point_tokens(m.group(2))
                ensure_point(p_target)
                for p in plane_pts: ensure_point(p)
                constraints.append(Constraint(type='point_on_plane', targets=[p_target] + plane_pts, value=0))
                logger.debug(f"[DSLParser]   + POINT_ON_PLANE: {p_target} on plane {plane_pts}")
                continue

            # PARALLEL(AB, CD)
            m = re.match(r'PARALLEL\(([^,]+),\s*([^)]+)\)', line)
            if m:
                seg1_pts = _parse_point_tokens(m.group(1))
                seg2_pts = _parse_point_tokens(m.group(2))
                if len(seg1_pts) >= 2 and len(seg2_pts) >= 2:
                    for p in seg1_pts[:2] + seg2_pts[:2]: ensure_point(p)
                    constraints.append(Constraint(type='parallel', targets=seg1_pts[:2] + seg2_pts[:2], value=0))
                    logger.debug(f"[DSLParser]   + PARALLEL: {seg1_pts[:2]} || {seg2_pts[:2]}")
                continue

            # PERPENDICULAR(AB, CD)
            m = re.match(r'PERPENDICULAR\(([^,]+),\s*([^)]+)\)', line)
            if m:
                seg1_pts = _parse_point_tokens(m.group(1))
                seg2_pts = _parse_point_tokens(m.group(2))
                if len(seg1_pts) >= 2 and len(seg2_pts) >= 2:
                    for p in seg1_pts[:2] + seg2_pts[:2]: ensure_point(p)
                    constraints.append(Constraint(type='perpendicular', targets=seg1_pts[:2] + seg2_pts[:2], value=0))
                    logger.debug(f"[DSLParser]   + PERPENDICULAR: {seg1_pts[:2]} _|_ {seg2_pts[:2]}")
                continue

            # MIDPOINT(M, AB) or MIDPOINT(M, A, B)
            m = re.match(r'MIDPOINT\(([^,]+),\s*(?:([^,]+),\s*([^)]+)|([^)]+))\)', line)
            if m:
                mid = m.group(1).strip()
                if m.group(2) and m.group(3):
                    p1, p2 = m.group(2).strip(), m.group(3).strip()
                else:
                    seg_pts = _parse_point_tokens(m.group(4))
                    p1, p2 = seg_pts[0], seg_pts[1] if len(seg_pts) > 1 else 'B'
                ensure_point(mid)
                ensure_point(p1)
                ensure_point(p2)
                constraints.append(Constraint(type='midpoint', targets=[mid, p1, p2], value=0))
                logger.debug(f"[DSLParser]   + MIDPOINT: {mid} = mid({p1}, {p2})")
                continue

            # SECTION(E, A, C, 0.66)
            m = re.match(r'SECTION\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([\d\.-]+)\)', line)
            if m:
                target, p1, p2, k = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), float(m.group(4))
                ensure_point(target)
                ensure_point(p1)
                ensure_point(p2)
                constraints.append(Constraint(type='section', targets=[target, p1, p2], value=k))
                logger.debug(f"[DSLParser]   + SECTION: {target} = {p1} + {k}({p2}-{p1})")
                continue

            # CIRCLE(O, r)
            m = re.match(r'CIRCLE\(([^,]+),\s*([\d\.]+)\)', line)
            if m:
                center, radius = m.group(1).strip(), float(m.group(2))
                ensure_point(center)
                constraints.append(Constraint(type='circle', targets=[center], value=radius))
                circles.append({"center": center, "radius": radius})
                logger.debug(f"[DSLParser]   + CIRCLE: center={center}, r={radius}")
                continue

            # SPHERE(O, r)
            m = re.match(r'SPHERE\(([^,]+),\s*([\d\.]+)\)', line)
            if m:
                is_3d = True
                center, radius = m.group(1).strip(), float(m.group(2))
                ensure_point(center)
                constraints.append(Constraint(type='sphere', targets=[center], value=radius))
                solids.append({"type": "sphere", "center": center, "radius": radius})
                logger.debug(f"[DSLParser]   + SPHERE: center={center}, r={radius}")
                continue

            # CONE(S, O, r) or CONE(S_O, r) or CONE(S, O, r, h)
            m = re.match(r'CONE\(([^,]+)(?:,\s*([^,]+))?,\s*([\d\.]+)(?:,\s*([\d\.]+))?\)', line)
            if m:
                is_3d = True
                if m.group(2):
                    apex, center = m.group(1).strip(), m.group(2).strip()
                elif '_' in m.group(1):
                    apex, center = [p.strip() for p in m.group(1).split('_', 1)]
                else:
                    apex, center = m.group(1).strip(), 'O'
                radius = float(m.group(3))
                height = float(m.group(4)) if m.group(4) else None
                ensure_point(apex)
                ensure_point(center)
                segments.append([apex, center])
                constraints.append(Constraint(type='segment', targets=[apex, center], value=0))
                constraints.append(Constraint(type='cone', targets=[apex, center], value=radius))
                if height is not None:
                    constraints.append(Constraint(type='length', targets=[apex, center], value=height))
                solids.append({"type": "cone", "apex": apex, "center": center, "radius": radius, "height": height})
                logger.debug(f"[DSLParser]   + CONE: apex={apex}, center={center}, r={radius}, h={height}")
                continue

            # CYLINDER(O1, O2, r) or CYLINDER(O1_O2, r)
            m = re.match(r'CYLINDER\(([^,]+)(?:,\s*([^,]+))?,\s*([\d\.]+)\)', line)
            if m:
                is_3d = True
                if m.group(2):
                    c1, c2 = m.group(1).strip(), m.group(2).strip()
                elif '_' in m.group(1):
                    c1, c2 = [p.strip() for p in m.group(1).split('_', 1)]
                else:
                    c1, c2 = 'O1', 'O2'
                radius = float(m.group(3))
                ensure_point(c1)
                ensure_point(c2)
                segments.append([c1, c2])
                constraints.append(Constraint(type='segment', targets=[c1, c2], value=0))
                constraints.append(Constraint(type='cylinder', targets=[c1, c2], value=radius))
                solids.append({"type": "cylinder", "center1": c1, "center2": c2, "radius": radius})
                logger.debug(f"[DSLParser]   + CYLINDER: c1={c1}, c2={c2}, r={radius}")
                continue

            # TETRAHEDRON(ABCD) or TETRAHEDRON(ABCD, a)
            m = re.match(r'TETRAHEDRON\(([^,)]+)(?:,\s*([\d\.]+))?\)', line)
            if m:
                is_3d = True
                pts = _parse_point_tokens(m.group(1))
                side_val = float(m.group(2)) if m.group(2) else None
                for p in pts: ensure_point(p)
                if len(pts) >= 4:
                    pA, pB, pC, pD = pts[0], pts[1], pts[2], pts[3]
                    # Generate all 6 edges
                    for p1, p2 in [(pA, pB), (pA, pC), (pA, pD), (pB, pC), (pC, pD), (pD, pB)]:
                        if [p1, p2] not in segments and [p2, p1] not in segments:
                            segments.append([p1, p2])
                            constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                        if side_val is not None:
                            constraints.append(Constraint(type='length', targets=[p1, p2], value=side_val))
                    if not polygon_order: polygon_order = [pB, pC, pD]
                    solids.append({"type": "tetrahedron", "apex": pA, "base": [pB, pC, pD], "points": pts[:4]})
                    logger.debug(f"[DSLParser]   + TETRAHEDRON: {pts[:4]}")
                continue

            # CUBE(ABCD_A1B1C1D1) or CUBE(ABCD_EFGH) or CUBE(..., a)
            m = re.match(r'CUBE\(([^,)]+)(?:,\s*([\d\.]+))?\)', line)
            if m:
                is_3d = True
                targets = m.group(1).strip()
                side_val = float(m.group(2)) if m.group(2) else None
                if '_' in targets:
                    b1_raw, b2_raw = targets.split('_', 1)
                    b1 = _parse_point_tokens(b1_raw)
                    b2 = _parse_point_tokens(b2_raw)
                else:
                    all_pts = _parse_point_tokens(targets)
                    b1, b2 = all_pts[:4], all_pts[4:8]
                for p in b1 + b2: ensure_point(p)
                _add_poly_segments(b1, segments, constraints)
                _add_poly_segments(b2, segments, constraints)
                for p1, p2 in zip(b1, b2):
                    if [p1, p2] not in segments and [p2, p1] not in segments:
                        segments.append([p1, p2])
                        constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                if side_val is not None:
                    for p1, p2 in zip(b1, b1[1:] + b1[:1]):
                        constraints.append(Constraint(type='length', targets=[p1, p2], value=side_val))
                    if b1 and b2:
                        constraints.append(Constraint(type='length', targets=[b1[0], b2[0]], value=side_val))
                if not polygon_order: polygon_order = list(b1)
                solids.append({"type": "cube", "base1": b1, "base2": b2, "points": b1 + b2})
                logger.debug(f"[DSLParser]   + CUBE: base1={b1}, base2={b2}")
                continue

            # CUBOID(ABCD_A1B1C1D1) or PARALLELEPIPED(...)
            m = re.match(r'(?:CUBOID|PARALLELEPIPED)\(([^)]+)\)', line)
            if m:
                is_3d = True
                targets = m.group(1).strip()
                if '_' in targets:
                    b1_raw, b2_raw = targets.split('_', 1)
                    b1 = _parse_point_tokens(b1_raw)
                    b2 = _parse_point_tokens(b2_raw)
                else:
                    all_pts = _parse_point_tokens(targets)
                    b1, b2 = all_pts[:4], all_pts[4:8]
                for p in b1 + b2: ensure_point(p)
                _add_poly_segments(b1, segments, constraints)
                _add_poly_segments(b2, segments, constraints)
                for p1, p2 in zip(b1, b2):
                    if [p1, p2] not in segments and [p2, p1] not in segments:
                        segments.append([p1, p2])
                        constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                if not polygon_order: polygon_order = list(b1)
                solids.append({"type": "cuboid", "base1": b1, "base2": b2, "points": b1 + b2})
                logger.debug(f"[DSLParser]   + CUBOID: base1={b1}, base2={b2}")
                continue

            # FRUSTUM(ABCD_EFGH) or TRUNCATED_PYRAMID(ABCD_EFGH)
            m = re.match(r'(?:FRUSTUM|TRUNCATED_PYRAMID)\(([^)]+)\)', line)
            if m:
                is_3d = True
                targets = m.group(1).strip()
                if '_' in targets:
                    b1_raw, b2_raw = targets.split('_', 1)
                    b1 = _parse_point_tokens(b1_raw)
                    b2 = _parse_point_tokens(b2_raw)
                else:
                    all_pts = _parse_point_tokens(targets)
                    n = len(all_pts) // 2
                    b1, b2 = all_pts[:n], all_pts[n:]
                for p in b1 + b2: ensure_point(p)
                _add_poly_segments(b1, segments, constraints)
                _add_poly_segments(b2, segments, constraints)
                for p1, p2 in zip(b1, b2):
                    if [p1, p2] not in segments and [p2, p1] not in segments:
                        segments.append([p1, p2])
                        constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                if not polygon_order: polygon_order = list(b1)
                solids.append({"type": "frustum", "base1": b1, "base2": b2, "points": b1 + b2})
                logger.debug(f"[DSLParser]   + FRUSTUM: base1={b1}, base2={b2}")
                continue

            # POLYGON_ORDER(A, B, C, D)
            m = re.match(r'POLYGON_ORDER\(([^)]+)\)', line)
            if m:
                polygon_order = _parse_point_tokens(m.group(1))
                logger.debug(f"[DSLParser]   + POLYGON_ORDER: {polygon_order}")
                continue

            # SEGMENT(M, N) or SEGMENT(MN)
            m = re.match(r'SEGMENT\(([^,]+)(?:,\s*([^)]+))?\)', line)
            if m:
                if m.group(2):
                    p1, p2 = m.group(1).strip(), m.group(2).strip()
                else:
                    pts = _parse_point_tokens(m.group(1))
                    p1, p2 = pts[0], pts[1] if len(pts) > 1 else 'B'
                ensure_point(p1)
                ensure_point(p2)
                segments.append([p1, p2])
                constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                logger.debug(f"[DSLParser]   + SEGMENT: {p1}—{p2}")
                continue

            # LINE(A, B)
            m = re.match(r'LINE\(([^,]+)(?:,\s*([^)]+))?\)', line)
            if m:
                if m.group(2):
                    p1, p2 = m.group(1).strip(), m.group(2).strip()
                else:
                    pts = _parse_point_tokens(m.group(1))
                    p1, p2 = pts[0], pts[1] if len(pts) > 1 else 'B'
                ensure_point(p1)
                ensure_point(p2)
                lines_ext.append([p1, p2])
                constraints.append(Constraint(type='line', targets=[p1, p2], value=0))
                logger.debug(f"[DSLParser]   + LINE: {p1}-{p2}")
                continue

            # RAY(A, B)
            m = re.match(r'RAY\(([^,]+)(?:,\s*([^)]+))?\)', line)
            if m:
                if m.group(2):
                    p1, p2 = m.group(1).strip(), m.group(2).strip()
                else:
                    pts = _parse_point_tokens(m.group(1))
                    p1, p2 = pts[0], pts[1] if len(pts) > 1 else 'B'
                ensure_point(p1)
                ensure_point(p2)
                rays.append([p1, p2])
                constraints.append(Constraint(type='ray', targets=[p1, p2], value=0))
                logger.debug(f"[DSLParser]   + RAY: {p1}->{p2}")
                continue

            # TRIANGLE(ABC) / PYRAMID(S_ABCD) / PRISM(ABC_DEF)
            m = re.match(r'(TRIANGLE|PYRAMID|PRISM)\(([^)]+)\)', line)
            if m:
                pt_type = m.group(1)
                targets = m.group(2)
                if pt_type in ["PYRAMID", "PRISM"]:
                    is_3d = True
                if pt_type == "TRIANGLE":
                    pts = _parse_point_tokens(targets)
                    for p in pts: ensure_point(p)
                    _add_poly_segments(pts, segments, constraints)
                    if not polygon_order: polygon_order = list(pts)
                elif pt_type == "PYRAMID":
                    # S_ABCD -> S is apex, ABCD is base
                    if "_" in targets:
                        apex_raw, base_raw = targets.split("_", 1)
                        apex = apex_raw.strip()
                        base = _parse_point_tokens(base_raw)
                        ensure_point(apex)
                        for p in base: ensure_point(p)
                        # Add segments from apex to all base points
                        for p in base:
                            if [apex, p] not in segments and [p, apex] not in segments:
                                segments.append([apex, p])
                                constraints.append(Constraint(type='segment', targets=[apex, p], value=0))
                        # Also add base polygon segments
                        _add_poly_segments(base, segments, constraints)
                        if not polygon_order: polygon_order = list(base)
                        solids.append({"type": "pyramid", "apex": apex, "base": base, "points": [apex] + base})
                elif pt_type == "PRISM":
                    # ABC_DEF -> two bases
                    if "_" in targets:
                        b1_raw, b2_raw = targets.split("_", 1)
                        b1 = _parse_point_tokens(b1_raw)
                        b2 = _parse_point_tokens(b2_raw)
                        for p in b1 + b2: ensure_point(p)
                        # Add base 1 segments
                        _add_poly_segments(b1, segments, constraints)
                        # Add base 2 segments
                        _add_poly_segments(b2, segments, constraints)
                        # Add lateral edges
                        for p1, p2 in zip(b1, b2):
                            if [p1, p2] not in segments and [p2, p1] not in segments:
                                segments.append([p1, p2])
                                constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                        if not polygon_order: polygon_order = list(b1)
                        solids.append({"type": "prism", "base1": b1, "base2": b2, "points": b1 + b2})
                logger.debug(f"[DSLParser]   + {pt_type}: {targets}")
                continue

            logger.warning(f"[DSLParser]   ? Unrecognized DSL line: '{line}'")

        logger.info(
            "[DSLParser] Parsed %d points, %d constraints, is_3d=%s.",
            len(points),
            len(constraints),
            is_3d,
        )

        # Safety sweep: Ensure all points referenced in constraints actually exist in the points dictionary
        for c in constraints:
            for pid in c.targets:
                if isinstance(pid, str) and pid not in points and not pid.replace('.', '', 1).isdigit():
                    points[pid] = Point(id=pid)
                    logger.debug(f"[DSLParser]   ! Auto-declared missing point from constraint: {pid}")

        # Attach metadata to synthetic constraints for downstream use
        if polygon_order:
            constraints.append(Constraint(type='polygon_order', targets=polygon_order, value=0))
        elif explicit_point_ids:
            constraints.append(Constraint(type='explicit_points', targets=explicit_point_ids, value=0))

        if lines_ext:
            constraints.append(Constraint(type='lines_metadata', targets=[",".join(l) for l in lines_ext], value=0))
        if rays:
            constraints.append(Constraint(type='rays_metadata', targets=[",".join(l) for l in rays], value=0))
        if solids:
            import json
            constraints.append(Constraint(type='solids_metadata', targets=[json.dumps(s) for s in solids], value=0))

        return list(points.values()), constraints, is_3d
