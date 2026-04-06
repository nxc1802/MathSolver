import asyncio
import logging
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine

logging.basicConfig(level=logging.DEBUG)

async def test_section_internal():
    print("\n--- Test: Section Point (Internal AE=2/3 AC) ---")
    dsl = """
    POINT(A)
    POINT(B)
    POINT(C)
    LENGTH(AB, 6)
    LENGTH(BC, 6)
    ANGLE(B, 90)
    SECTION(E, A, C, 0.6667)
    """
    parser = DSLParser()
    engine = GeometryEngine()
    
    pts, constraints = parser.parse(dsl)
    result = engine.solve(pts, constraints)
    
    if result:
        coords = result['coordinates']
        print(f"  A: {coords['A']}")
        print(f"  C: {coords['C']}")
        print(f"  E: {coords['E']}")
        
        # Verify AE = 0.6667 * AC
        import math
        def dist(p1, p2): return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        
        d_ac = dist(coords['A'], coords['C'])
        d_ae = dist(coords['A'], coords['E'])
        ratio = d_ae / d_ac
        print(f"  Calculated Ratio AE/AC: {ratio:.4f} (Expected: 0.6667)")
        assert abs(ratio - 0.6667) < 1e-4
    else:
        print("  ❌ Solve failed")

async def test_section_external():
    print("\n--- Test: Section Point (External AE=2*AC) ---")
    dsl = """
    POINT(A)
    POINT(C)
    LENGTH(AC, 5)
    SECTION(E, A, C, 2.0)
    """
    parser = DSLParser()
    engine = GeometryEngine()
    
    pts, constraints = parser.parse(dsl)
    result = engine.solve(pts, constraints)
    
    if result:
        coords = result['coordinates']
        print(f"  A: {coords['A']}")
        print(f"  C: {coords['C']}")
        print(f"  E: {coords['E']}")
        
        import math
        def dist(p1, p2): return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        d_ac = dist(coords['A'], coords['C'])
        d_ae = dist(coords['A'], coords['E'])
        print(f"  AE: {d_ae}, AC: {d_ac}, Ratio: {d_ae/d_ac}")
        assert abs(d_ae/d_ac - 2.0) < 1e-4
    else:
        print("  ❌ Solve failed")

async def test_line_ray_metadata():
    print("\n--- Test: Line and Ray Metadata ---")
    dsl = """
    POINT(A)
    POINT(B)
    LINE(A, B)
    RAY(A, B)
    """
    parser = DSLParser()
    engine = GeometryEngine()
    
    pts, constraints = parser.parse(dsl)
    result = engine.solve(pts, constraints)
    
    if result:
        print(f"  Lines: {result.get('lines')}")
        print(f"  Rays: {result.get('rays')}")
        assert ['A', 'B'] in result.get('lines', [])
        assert ['A', 'B'] in result.get('rays', [])
        print("  ✅ Metadata present")
    else:
        print("  ❌ Solve failed")

if __name__ == "__main__":
    asyncio.run(test_section_internal())
    asyncio.run(test_section_external())
    asyncio.run(test_line_ray_metadata())
