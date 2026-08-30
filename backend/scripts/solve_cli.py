import asyncio
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import Orchestrator


async def main():
    if len(sys.argv) < 2:
        problem = "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10. SO vuông góc với mặt phẳng (ABCD) tại tâm O, SO=15. Tính thể tích khối chóp."
    else:
        problem = " ".join(sys.argv[1:])

    print(f"\n🚀 [AI Core CLI] Solving: {problem}\n" + "=" * 60)
    orchestrator = Orchestrator()
    result = await orchestrator.run(text=problem, job_id="cli_test")

    print("\n✅ Status:", result.get("status"))
    print("\n📐 Generated Geometry DSL:")
    print("-" * 40)
    print(result.get("geometry_dsl"))

    print("\n📍 Calculated 3D Coordinates:")
    print("-" * 40)
    for p, c in (result.get("coordinates") or {}).items():
        print(f"  {p}: {c}")

    print("\n🧮 Step-by-Step Mathematical Solution:")
    print("-" * 40)
    sol = result.get("solution") or {}
    print(f"Answer: {sol.get('answer')}")
    for step in sol.get("steps", []):
        print(f"  • {step}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
