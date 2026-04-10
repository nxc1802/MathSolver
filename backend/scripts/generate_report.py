import json
import os
import sys
from datetime import datetime

def generate_report(json_path, report_path):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        with open(report_path, 'w') as f:
            f.write('# Báo cáo Kiểm thử API Toàn diện (Full Suite API Report)\n\n')
            f.write(f'**Thời gian chạy:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'**Kết quả chung:** {"✅ PASS" if all(r.get("success", False) for r in data) else "❌ FAIL"}\n\n')
            
            f.write('| ID | Câu hỏi (Query) | Trạng thái | Thời gian (s) | Kết quả / Lỗi |\n')
            f.write('| :--- | :--- | :--- | :--- | :--- |\n')
            for r in data:
                status = "✅ PASS" if r.get("success") else "❌ FAIL"
                elapsed = f"{r.get('elapsed', 0):.2f}"
                query = r.get('query', '-')
                
                # Extract analysis or error
                res = r.get('result', {})
                if not isinstance(res, dict):
                    res = {}
                
                analysis = res.get('semantic_analysis', '-')
                if not r.get("success"):
                    analysis = f"**Lỗi:** {r.get('error', '-')}"
                
                # Truncate long analysis for table
                short_analysis = (analysis[:100] + '...') if len(analysis) > 100 else analysis
                
                f.write(f'| {r["id"]} | {query} | {status} | {elapsed} | {short_analysis} |\n')
            
            f.write('\n---\n**Chi tiết Output (DSL & Analysis):**\n')
            for r in data:
                if r.get('success'):
                    res = r.get('result', {})
                    if not isinstance(res, dict):
                        continue
                        
                    f.write(f"\n### Case {r['id']}: {r.get('query')}\n")
                    f.write(f"**Semantic Analysis:**\n{res.get('semantic_analysis', '-')}\n\n")
                    f.write(f"**Geometry DSL:**\n```\n{res.get('geometry_dsl', '-')}\n```\n")
                    
                    # v5.1 Solution info
                    sol = res.get('solution')
                    if sol and isinstance(sol, dict):
                        f.write("**Solution (v5.1):**\n")
                        f.write(f"- **Answer:** {sol.get('answer', 'N/A')}\n")
                        f.write("- **Steps:**\n")
                        steps = sol.get('steps', [])
                        if steps:
                            for step in steps:
                                f.write(f"  - {step}\n")
                        else:
                            f.write("  - (Không có bước giải cụ thể)\n")
                        
                        if sol.get('symbolic_expression'):
                            f.write(f"- **Symbolic:** `{sol.get('symbolic_expression')}`\n")
                        f.write("\n")
            
        print(f'Report generated: {report_path}')
    except Exception as e:
        print(f'Error generating report: {e}')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <json_results> <report_output>")
        sys.exit(1)
    generate_report(sys.argv[1], sys.argv[2])
