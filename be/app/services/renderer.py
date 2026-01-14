from typing import Dict, Any, List
import math


class RendererService:
    """Service for rendering geometry to SVG."""
    
    def __init__(self, width: int = 400, height: int = 400):
        self.width = width
        self.height = height
        self.padding = 40
    
    def render_svg(self, points: List[Dict], shapes: List[Dict]) -> str:
        """
        Render points and shapes to SVG.
        
        Args:
            points: List of point dicts with name, x, y
            shapes: List of shape dicts with type, vertices, etc.
            
        Returns:
            SVG string
        """
        if not points:
            return self._empty_svg()
        
        # Calculate bounds
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        range_x = max_x - min_x or 1
        range_y = max_y - min_y or 1
        
        scale = min(
            (self.width - 2 * self.padding) / range_x,
            (self.height - 2 * self.padding) / range_y
        )
        
        offset_x = self.padding + ((self.width - 2 * self.padding) - range_x * scale) / 2
        offset_y = self.padding + ((self.height - 2 * self.padding) - range_y * scale) / 2
        
        def tx(x): return offset_x + (x - min_x) * scale
        def ty(y): return self.height - (offset_y + (y - min_y) * scale)
        
        # Build SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">',
            '<defs>',
            '  <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">',
            '    <stop offset="0%" style="stop-color:#6366f1;stop-opacity:0.3" />',
            '    <stop offset="100%" style="stop-color:#22d3ee;stop-opacity:0.1" />',
            '  </linearGradient>',
            '</defs>',
            f'<rect width="{self.width}" height="{self.height}" fill="#0f0f23"/>',
            # Grid
            '<g stroke="#2d2d4a" stroke-width="0.5">',
        ]
        
        # Draw grid
        for i in range(0, self.width, 20):
            svg_parts.append(f'  <line x1="{i}" y1="0" x2="{i}" y2="{self.height}"/>')
        for i in range(0, self.height, 20):
            svg_parts.append(f'  <line x1="0" y1="{i}" x2="{self.width}" y2="{i}"/>')
        svg_parts.append('</g>')
        
        # Draw shapes (triangles, etc.)
        for shape in shapes:
            if shape['type'] == 'triangle':
                vertices = shape.get('vertices', [])
                if len(vertices) == 3:
                    pts = []
                    for v in vertices:
                        p = next((p for p in points if p['name'] == v), None)
                        if p:
                            pts.append(f"{tx(p['x'])},{ty(p['y'])}")
                    if len(pts) == 3:
                        svg_parts.append(
                            f'<polygon points="{" ".join(pts)}" '
                            f'fill="url(#grad1)" stroke="#6366f1" stroke-width="2"/>'
                        )
        
        # Draw points
        for p in points:
            px, py = tx(p['x']), ty(p['y'])
            svg_parts.append(
                f'<circle cx="{px}" cy="{py}" r="6" fill="#22d3ee" stroke="#0f766e" stroke-width="2"/>'
            )
            svg_parts.append(
                f'<text x="{px}" y="{py - 15}" text-anchor="middle" '
                f'fill="#f0f0f0" font-family="Inter, sans-serif" font-size="14" font-weight="bold">'
                f'{p["name"]}</text>'
            )
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
    
    def _empty_svg(self) -> str:
        """Return empty placeholder SVG."""
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">
  <rect width="{self.width}" height="{self.height}" fill="#0f0f23"/>
  <text x="{self.width/2}" y="{self.height/2}" text-anchor="middle" fill="#4a4a6a" font-family="Inter, sans-serif" font-size="16">
    Hình sẽ được vẽ tại đây
  </text>
</svg>'''
    
    def dsl_to_svg(self, dsl: str) -> str:
        """Convert DSL to SVG."""
        points = []
        shapes = []
        
        for line in dsl.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse POINT(name, x, y)
            import re
            point_match = re.match(r'POINT\((\w+),\s*([-\d.]+),\s*([-\d.]+)\)', line)
            if point_match:
                points.append({
                    'name': point_match.group(1),
                    'x': float(point_match.group(2)),
                    'y': float(point_match.group(3)),
                })
            
            # Parse TRIANGLE(name, A, B, C)
            tri_match = re.match(r'TRIANGLE\((\w+),\s*(\w+),\s*(\w+),\s*(\w+)\)', line)
            if tri_match:
                shapes.append({
                    'type': 'triangle',
                    'name': tri_match.group(1),
                    'vertices': [tri_match.group(2), tri_match.group(3), tri_match.group(4)],
                })
        
        return self.render_svg(points, shapes)
