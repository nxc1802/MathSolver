import re
from .models import Point, Constraint

class DSLParser:
    def __init__(self):
        self.points = {}
        self.constraints = []

    def parse(self, text: str):
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Match POINT(A)
            point_match = re.match(r'POINT\((\w+)\)', line)
            if point_match:
                name = point_match.group(1)
                self.points[name] = Point(id=name)
                continue

            # Match LENGTH(AB, 5)
            length_match = re.match(r'LENGTH\((\w+), ([\d\.]+)\)', line)
            if length_match:
                target = length_match.group(1)
                value = float(length_match.group(2))
                # AB translates to points A and B
                pts = [target[i:i+1] for i in range(len(target))]
                self.constraints.append(Constraint(type='length', targets=pts, value=value))
                continue

            # Match ANGLE(A, 60deg)
            angle_match = re.match(r'ANGLE\((\w+), ([\d\.]+)deg\)', line)
            if angle_match:
                target = angle_match.group(1)
                value = float(angle_match.group(2))
                self.constraints.append(Constraint(type='angle', targets=[target], value=value))
                continue

        return list(self.points.values()), self.constraints
