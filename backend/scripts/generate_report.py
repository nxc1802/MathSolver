import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime


def _parse_junit_xml(path: str) -> dict:
    """Summarize pytest junitxml (JUnit) file."""
    out = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        nodes = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        for ts in nodes:
            if ts.tag != "testsuite":
                continue
            out["tests"] += int(ts.attrib.get("tests", 0) or 0)
            out["failures"] += int(ts.attrib.get("failures", 0) or 0)
            out["errors"] += int(ts.attrib.get("errors", 0) or 0)
            out["skipped"] += int(ts.attrib.get("skipped", 0) or 0)
            out["time"] += float(ts.attrib.get("time", 0) or 0)
    except Exception as e:
        out["parse_error"] = str(e)
    return out


def generate_report(json_path: str, report_path: str, junit_path: str | None = None) -> None:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        junit_summary = None
        if junit_path and os.path.isfile(junit_path):
            junit_summary = _parse_junit_xml(junit_path)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Báo cáo Kiểm thử tích hợp Backend (Integration Report)\n\n")
            f.write(f"**Thời gian chạy:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            suite_ok = all(r.get("success", False) for r in data) if isinstance(data, list) else False
            f.write(f"**API suite (JSON):** {'PASS' if suite_ok else 'FAIL'}\n")

            if junit_summary and "parse_error" not in junit_summary:
                j_ok = junit_summary["failures"] == 0 and junit_summary["errors"] == 0
                f.write(
                    f"**Pytest (JUnit):** {'PASS' if j_ok else 'FAIL'} — "
                    f"tests={junit_summary['tests']}, failures={junit_summary['failures']}, "
                    f"errors={junit_summary['errors']}, skipped={junit_summary['skipped']}, "
                    f"time_s={junit_summary['time']:.2f}\n"
                )
            elif junit_summary and "parse_error" in junit_summary:
                f.write(f"**Pytest (JUnit):** (could not parse: {junit_summary['parse_error']})\n")

            f.write("\n")

            f.write("| ID | Câu hỏi (Query) | Trạng thái | Thời gian (s) | Kết quả / Lỗi |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for r in data:
                status = "PASS" if r.get("success") else "FAIL"
                elapsed = f"{float(r.get('elapsed', 0) or 0):.2f}"
                query = r.get("query", "-")

                res = r.get("result", {})
                if not isinstance(res, dict):
                    res = {}

                analysis = res.get("semantic_analysis", "-")
                if not r.get("success"):
                    analysis = f"**Lỗi:** {r.get('error', '-')}"

                short_analysis = (analysis[:100] + "...") if len(str(analysis)) > 100 else analysis

                f.write(f"| {r['id']} | {query} | {status} | {elapsed} | {short_analysis} |\n")

            f.write("\n---\n**Chi tiết Output (DSL & Analysis):**\n")
            for r in data:
                if not r.get("success"):
                    continue
                res = r.get("result", {})
                if not isinstance(res, dict):
                    continue

                f.write(f"\n### Case {r['id']}: {r.get('query')}\n")
                f.write(f"**Semantic Analysis:**\n{res.get('semantic_analysis', '-')}\n\n")
                f.write(f"**Geometry DSL:**\n```\n{res.get('geometry_dsl', '-')}\n```\n")

                sol = res.get("solution")
                if sol and isinstance(sol, dict):
                    f.write("**Solution (v5.1):**\n")
                    f.write(f"- **Answer:** {sol.get('answer', 'N/A')}\n")
                    f.write("- **Steps:**\n")
                    steps = sol.get("steps", [])
                    if steps:
                        for step in steps:
                            f.write(f"  - {step}\n")
                    else:
                        f.write("  - (Không có bước giải cụ thể)\n")

                    if sol.get("symbolic_expression"):
                        f.write(f"- **Symbolic:** `{sol.get('symbolic_expression')}`\n")
                    f.write("\n")

        print(f"Report generated: {report_path}")
    except Exception as e:
        print(f"Error generating report: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python generate_report.py <json_results> <report_output> [junit_xml_optional]"
        )
        sys.exit(1)
    junit = sys.argv[3] if len(sys.argv) > 3 else None
    generate_report(sys.argv[1], sys.argv[2], junit)
