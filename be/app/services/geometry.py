from typing import Dict, Any, List, Tuple, Optional
import math
from dataclasses import dataclass
import sympy as sp
from sympy.geometry import Point, Line, Segment, Triangle, Circle


@dataclass
class GeometryPoint:
    """A point in 2D/3D space."""
    name: str
    x: float
    y: float
    z: Optional[float] = None


@dataclass
class RenderCommand:
    """A command for the rendering engine."""
    command_type: str
    params: Dict[str, Any]


class GeometryEngine:
    """
    Engine for geometric calculations and validation.
    Uses SymPy for symbolic math - deterministic, not LLM-dependent.
    """
    
    def __init__(self):
        self.points: Dict[str, GeometryPoint] = {}
        self.objects: Dict[str, Any] = {}
    
    def add_point(self, name: str, x: float, y: float, z: Optional[float] = None):
        """Add a point to the scene."""
        self.points[name] = GeometryPoint(name, x, y, z)
        return self.points[name]
    
    def calculate_distance(self, p1_name: str, p2_name: str) -> float:
        """Calculate distance between two points."""
        p1 = self.points.get(p1_name)
        p2 = self.points.get(p2_name)
        
        if not p1 or not p2:
            raise ValueError(f"Points {p1_name} or {p2_name} not found")
        
        if p1.z is not None and p2.z is not None:
            # 3D distance
            return math.sqrt(
                (p2.x - p1.x)**2 + 
                (p2.y - p1.y)**2 + 
                (p2.z - p1.z)**2
            )
        else:
            # 2D distance
            return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
    
    def calculate_triangle_from_sas(
        self,
        side_a: float,
        angle_degrees: float,
        side_b: float
    ) -> Tuple[float, float, float]:
        """
        Calculate third side and area using Side-Angle-Side.
        
        Args:
            side_a: Length of first side
            angle_degrees: Angle between the two sides in degrees
            side_b: Length of second side
            
        Returns:
            Tuple of (third_side, area, perimeter)
        """
        angle_rad = math.radians(angle_degrees)
        
        # Law of cosines: c² = a² + b² - 2ab*cos(C)
        third_side = math.sqrt(
            side_a**2 + side_b**2 - 2 * side_a * side_b * math.cos(angle_rad)
        )
        
        # Area = 0.5 * a * b * sin(C)
        area = 0.5 * side_a * side_b * math.sin(angle_rad)
        
        perimeter = side_a + side_b + third_side
        
        return (round(third_side, 4), round(area, 4), round(perimeter, 4))
    
    def create_triangle_points(
        self,
        name: str,
        side_ab: float,
        side_ac: float,
        angle_a_degrees: float
    ) -> Dict[str, GeometryPoint]:
        """
        Create triangle points with A at origin.
        
        Returns dict with points A, B, C.
        """
        angle_rad = math.radians(angle_a_degrees)
        
        # A at origin
        a = self.add_point("A", 0, 0)
        
        # B along x-axis
        b = self.add_point("B", side_ab, 0)
        
        # C at angle from A
        c = self.add_point("C", 
            side_ac * math.cos(angle_rad),
            side_ac * math.sin(angle_rad)
        )
        
        return {"A": a, "B": b, "C": c}
    
    def parse_dsl(self, dsl_code: str) -> List[RenderCommand]:
        """
        Parse Geometry DSL into render commands.
        
        Args:
            dsl_code: DSL code string
            
        Returns:
            List of RenderCommand objects
        """
        commands = []
        
        for line in dsl_code.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse command
            if line.startswith('POINT('):
                # POINT(name, x, y)
                params_str = line[6:-1]
                parts = [p.strip() for p in params_str.split(',')]
                commands.append(RenderCommand(
                    command_type='point',
                    params={
                        'name': parts[0],
                        'x': float(parts[1]),
                        'y': float(parts[2]),
                    }
                ))
            elif line.startswith('TRIANGLE('):
                # TRIANGLE(name, A, B, C)
                params_str = line[9:-1]
                parts = [p.strip() for p in params_str.split(',')]
                commands.append(RenderCommand(
                    command_type='triangle',
                    params={
                        'name': parts[0],
                        'vertices': parts[1:4],
                    }
                ))
            elif line.startswith('STEP('):
                # STEP("description")
                desc = line[5:-1].strip('"\'')
                commands.append(RenderCommand(
                    command_type='step',
                    params={'description': desc}
                ))
            elif line.startswith('ANIMATE_DRAW('):
                # ANIMATE_DRAW(object, duration)
                params_str = line[13:-1]
                parts = [p.strip() for p in params_str.split(',')]
                commands.append(RenderCommand(
                    command_type='animate_draw',
                    params={
                        'object': parts[0],
                        'duration': parts[1] if len(parts) > 1 else '1s',
                    }
                ))
        
        return commands
    
    def validate_geometry(self, commands: List[RenderCommand]) -> Dict[str, Any]:
        """
        Validate geometry commands for consistency.
        
        Returns validation result with any errors.
        """
        errors = []
        warnings = []
        
        defined_points = set()
        defined_objects = set()
        
        for cmd in commands:
            if cmd.command_type == 'point':
                name = cmd.params.get('name')
                if name in defined_points:
                    warnings.append(f"Point {name} redefined")
                defined_points.add(name)
                
            elif cmd.command_type == 'triangle':
                vertices = cmd.params.get('vertices', [])
                for v in vertices:
                    if v not in defined_points:
                        errors.append(f"Triangle vertex {v} not defined")
                defined_objects.add(cmd.params.get('name'))
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
