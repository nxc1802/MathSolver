import re
import logging
from typing import List, Tuple, Dict, Any
from .models import Point, Constraint

logger = logging.getLogger(__name__)


class DSLParser:
    def parse(self, text: str) -> Tuple[List[Point], List[Constraint]]:
        """Parse DSL text into points and constraints. Stateless per call."""
        points: Dict[str, Point] = {}
        constraints: List[Constraint] = []
        polygon_order: List[str] = []
        circles: List[Dict[str, Any]] = []
        segments: List[List[str]] = []

        logger.info("==[DSLParser] Parsing DSL input==")
        logger.debug(f"[DSLParser] Raw DSL:\n{text}")

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue

            # POINT(A)
            m = re.match(r'POINT\((\w+)\)', line)
            if m:
                name = m.group(1)
                points[name] = Point(id=name)
                logger.debug(f"[DSLParser]   + POINT: {name}")
                continue

            # LENGTH(AB, 5)
            m = re.match(r'LENGTH\((\w+),\s*([\d\.]+)\)', line)
            if m:
                target, value = m.group(1), float(m.group(2))
                pts = [target[i:i+1] for i in range(len(target))]
                constraints.append(Constraint(type='length', targets=pts, value=value))
                logger.debug(f"[DSLParser]   + LENGTH: {pts} = {value}")
                continue

            # ANGLE(A, 90) or ANGLE(A, 90deg)
            m = re.match(r'ANGLE\((\w+),\s*([\d\.]+)(?:deg)?\)', line)
            if m:
                target, value = m.group(1), float(m.group(2))
                constraints.append(Constraint(type='angle', targets=[target], value=value))
                logger.debug(f"[DSLParser]   + ANGLE: vertex={target}, degrees={value}")
                continue

            # PARALLEL(AB, CD)
            m = re.match(r'PARALLEL\((\w+),\s*(\w+)\)', line)
            if m:
                seg1, seg2 = m.group(1), m.group(2)
                constraints.append(Constraint(type='parallel', targets=list(seg1) + list(seg2), value=0))
                logger.debug(f"[DSLParser]   + PARALLEL: {seg1} || {seg2}")
                continue

            # PERPENDICULAR(AB, CD)
            m = re.match(r'PERPENDICULAR\((\w+),\s*(\w+)\)', line)
            if m:
                seg1, seg2 = m.group(1), m.group(2)
                constraints.append(Constraint(type='perpendicular', targets=list(seg1) + list(seg2), value=0))
                logger.debug(f"[DSLParser]   + PERPENDICULAR: {seg1} _|_ {seg2}")
                continue

            # MIDPOINT(M, AB)  — M is midpoint of AB
            m = re.match(r'MIDPOINT\((\w+),\s*(\w+)\)', line)
            if m:
                mid, seg = m.group(1), m.group(2)
                if mid not in points:
                    points[mid] = Point(id=mid)
                pts = [mid] + [seg[i:i+1] for i in range(len(seg))]
                constraints.append(Constraint(type='midpoint', targets=pts, value=0))
                logger.debug(f"[DSLParser]   + MIDPOINT: {mid} = mid({seg})")
                continue

            # CIRCLE(O, r)
            m = re.match(r'CIRCLE\((\w+),\s*([\d\.]+)\)', line)
            if m:
                center, radius = m.group(1), float(m.group(2))
                if center not in points:
                    points[center] = Point(id=center)
                constraints.append(Constraint(type='circle', targets=[center], value=radius))
                circles.append({"center": center, "radius": radius})
                logger.debug(f"[DSLParser]   + CIRCLE: center={center}, r={radius}")
                continue

            # POLYGON_ORDER(A, B, C, D) — thứ tự nối điểm để vẽ đa giác
            m = re.match(r'POLYGON_ORDER\(([^)]+)\)', line)
            if m:
                polygon_order = [p.strip() for p in m.group(1).split(',')]
                logger.debug(f"[DSLParser]   + POLYGON_ORDER: {polygon_order}")
                continue

            # SEGMENT(M, N) — đoạn thẳng phụ cần vẽ
            m = re.match(r'SEGMENT\((\w+),\s*(\w+)\)', line)
            if m:
                p1, p2 = m.group(1), m.group(2)
                segments.append([p1, p2])
                constraints.append(Constraint(type='segment', targets=[p1, p2], value=0))
                logger.debug(f"[DSLParser]   + SEGMENT: {p1}—{p2}")
                continue

            # TRIANGLE(ABC) — gợi ý vẽ tam giác (polygon_order fallback)
            m = re.match(r'TRIANGLE\((\w+)\)', line)
            if m:
                tri = m.group(1)
                if not polygon_order:
                    polygon_order = list(tri)
                logger.debug(f"[DSLParser]   + TRIANGLE: {tri}")
                continue

            logger.warning(f"[DSLParser]   ? Unrecognized DSL line: '{line}'")

        logger.info(f"[DSLParser] Parsed {len(points)} points, {len(constraints)} constraints.")

        # Attach metadata to a synthetic constraint for downstream use
        if polygon_order:
            constraints.append(Constraint(type='polygon_order', targets=polygon_order, value=0))
        if circles:
            for c in circles:
                # already added individually above
                pass

        return list(points.values()), constraints
