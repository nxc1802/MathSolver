from openai import AsyncOpenAI
from typing import Dict, Any
import json

from app.config import get_settings

settings = get_settings()


class LLMService:
    """Service for interacting with LLM via MegaLLM API."""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.megallm_api_key,
            base_url=settings.megallm_base_url,
        )
        self.model = settings.megallm_model
    
    async def solve(self, problem_text: str) -> Dict[str, Any]:
        """
        Solve a math problem using LLM reasoning.
        
        Args:
            problem_text: The math problem in text form
            
        Returns:
            Dictionary with steps, answer, and problem_type
        """
        system_prompt = """Bạn là một giáo viên toán chuyên nghiệp. 
Hãy giải bài toán theo từng bước rõ ràng.

Trả về kết quả dưới dạng JSON với format:
{
    "problem_type": "algebra" | "geometry_2d" | "geometry_3d" | "oxyz",
    "steps": [
        {
            "step_number": 1,
            "description": "Mô tả bước giải",
            "formula": "công thức sử dụng (nếu có)",
            "result": "kết quả của bước này"
        }
    ],
    "answer": "Đáp án cuối cùng",
    "geometry_dsl": "Các lệnh vẽ hình (nếu là bài hình học)"
}

Chỉ trả về JSON, không có text khác."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": problem_text}
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                # Try to extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                result = json.loads(content.strip())
            except json.JSONDecodeError:
                # If not valid JSON, wrap in basic structure
                result = {
                    "problem_type": "unknown",
                    "steps": [{"step_number": 1, "description": content, "formula": None, "result": ""}],
                    "answer": content,
                }
            
            return result
            
        except Exception as e:
            # Return error structure
            return {
                "problem_type": "error",
                "steps": [{"step_number": 1, "description": f"Lỗi: {str(e)}", "formula": None, "result": ""}],
                "answer": f"Error: {str(e)}",
            }
    
    async def generate_geometry_dsl(self, problem_structure: Dict) -> str:
        """Generate Geometry DSL from problem structure."""
        prompt = f"""Dựa trên cấu trúc bài toán sau, sinh ra Geometry DSL để vẽ hình:

{json.dumps(problem_structure, ensure_ascii=False, indent=2)}

Geometry DSL format:
- POINT(name, x, y)
- SEGMENT(name, point1, point2)
- TRIANGLE(name, A, B, C)
- CIRCLE(name, center, radius)
- STEP("description")
- ANIMATE_DRAW(object, duration)

Chỉ trả về DSL code, không có giải thích."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"# Error generating DSL: {str(e)}"
