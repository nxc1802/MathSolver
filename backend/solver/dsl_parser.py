import re
import logging
from .models import Point, Constraint

logger = logging.getLogger(__name__)

class DSLParser:
    def parse(self, text: str):
        """Parse DSL text into points and constraints. Stateless per call."""
        points = {}
        constraints = []
        
        logger.info("==[DSLParser] Parsing DSL input==")
        logger.debug(f"[DSLParser] Raw DSL:\n{text}")

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue

            # Match POINT(A)
            point_match = re.match(r'POINT\((\w+)\)', line)
            if point_match:
                name = point_match.group(1)
                points[name] = Point(id=name)
                logger.debug(f"[DSLParser]   + POINT: {name}")
                continue

            # Match LENGTH(AB, 5)
            length_match = re.match(r'LENGTH\((\w+),\s*([\d\.]+)\)', line)
            if length_match:
                target = length_match.group(1)
                value = float(length_match.group(2))
                pts = [target[i:i+1] for i in range(len(target))]
                constraints.append(Constraint(type='length', targets=pts, value=value))
                logger.debug(f"[DSLParser]   + LENGTH: {pts} = {value}")
                continue

            # Match ANGLE(A, 60deg) or ANGLE(A, 60)
            angle_match = re.match(r'ANGLE\((\w+),\s*([\d\.]+)(?:deg)?\)', line)
            if angle_match:
                target = angle_match.group(1)
                value = float(angle_match.group(2))
                constraints.append(Constraint(type='angle', targets=[target], value=value))
                logger.debug(f"[DSLParser]   + ANGLE: vertex={target}, degrees={value}")
                continue

            # Match PARALLEL(AB, CD)
            parallel_match = re.match(r'PARALLEL\((\w+),\s*(\w+)\)', line)
            if parallel_match:
                seg1, seg2 = parallel_match.group(1), parallel_match.group(2)
                pts = list(seg1) + list(seg2)
                constraints.append(Constraint(type='parallel', targets=pts, value=0))
                logger.debug(f"[DSLParser]   + PARALLEL: {seg1} || {seg2}")
                continue

            # Match PERPENDICULAR(AB, CD)
            perp_match = re.match(r'PERPENDICULAR\((\w+),\s*(\w+)\)', line)
            if perp_match:
                seg1, seg2 = perp_match.group(1), perp_match.group(2)
                pts = list(seg1) + list(seg2)
                constraints.append(Constraint(type='perpendicular', targets=pts, value=0))
                logger.debug(f"[DSLParser]   + PERPENDICULAR: {seg1} _|_ {seg2}")
                continue

            logger.warning(f"[DSLParser]   ? Unrecognized DSL line: '{line}'")

        logger.info(f"[DSLParser] Parsed {len(points)} points, {len(constraints)} constraints.")
        return list(points.values()), constraints
