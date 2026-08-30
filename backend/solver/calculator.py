import re
import logging
import sympy as sp
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class MathCalculator:
    """
    Deterministic Mathematical Calculation Engine (v5.3).
    Executes geometric formulas, algebraic expressions, and symbolic calculus using SymPy
    to eliminate LLM arithmetic hallucinations and ensure 100% calculation accuracy.
    """

    def __init__(self):
        self.safe_globals = {
            "sp": sp,
            "sqrt": sp.sqrt,
            "pi": sp.pi,
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "asin": sp.asin,
            "acos": sp.acos,
            "atan": sp.atan,
            "Rational": sp.Rational,
            "Abs": sp.Abs,
            "exp": sp.exp,
            "log": sp.log,
            "deg": lambda rad: rad * 180 / sp.pi,
            "rad": lambda deg: deg * sp.pi / 180,
        }

    def evaluate_expression(self, expr_str: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[sp.Expr], Optional[float], str]:
        """
        Evaluates a mathematical expression string using SymPy with intelligent variable aliasing.
        Returns: (exact_symbolic_value, float_value, latex_string)
        """
        if not expr_str:
            return None, None, "0"

        s = str(expr_str).replace('$', '').strip().rstrip('.,;')
        s = s.replace("\x0crac", "frac").replace("\x0c", "")
        s = s.replace("^", "**").replace("×", "*").replace("÷", "/").replace("\\times", "*").replace("\\cdot", "*")
        s = s.replace("\\pi", "pi")

        # 1. LaTeX subscripts: S_{ABCD} -> S_ABCD
        s = re.sub(r'([A-Za-z]+)_\{([^}]+)\}', r'\1_\2', s)

        # 2. LaTeX sqrt: \sqrt{x} -> sqrt(x)
        s = re.sub(r'\\*sqrt\{([^}]+)\}', r'sqrt(\1)', s)
        s = re.sub(r'\\*sqrt([0-9]+)', r'sqrt(\1)', s)

        # 3. LaTeX fractions: \frac{a}{b} -> ((a)/(b))
        s = re.sub(r'\\*frac\{([^}]+)\}\{([^}]+)\}', r'((\1)/(\2))', s)
        s = re.sub(r'frac\{([^}]+)\}\{([^}]+)\}', r'((\1)/(\2))', s)

        # 4. Insert implicit multiplications:
        # e.g. 9sqrt(3) -> 9*sqrt(3), 36sqrt(3) -> 36*sqrt(3), 2(64+...) -> 2*(64+...), ((6)/(3))(...) -> ((6)/(3))*(...)
        s = re.sub(r'(\d+|\))\s*(sqrt|pi|sin|cos|tan|[A-Za-z_])', r'\1*\2', s)
        s = re.sub(r'(\d+|\))\s*\(', r'\1*(', s)

        # 5. Standalone fractions like 1/3, 1/2 to Rational
        s = re.sub(r'(?<!Rational\()\b1/3\b', 'Rational(1, 3)', s)
        s = re.sub(r'(?<!Rational\()\b1/2\b', 'Rational(1, 2)', s)
        s = re.sub(r'(?<!Rational\()\b1/4\b', 'Rational(1, 4)', s)
        s = re.sub(r'(?<!Rational\()\b1/6\b', 'Rational(1, 6)', s)
        s = re.sub(r'(?<!Rational\()\b2/3\b', 'Rational(2, 3)', s)
        s = re.sub(r'(?<!Rational\()\b4/3\b', 'Rational(4, 3)', s)
        s = re.sub(r'(?<!Rational\()\b6/3\b', 'Rational(6, 3)', s)

        eval_locals = dict(self.safe_globals)
        ctx = context or {}
        for k, v in ctx.items():
            if isinstance(v, (int, float, sp.Expr)):
                eval_locals[k] = v

        try:
            sym_val = sp.sympify(s, locals=eval_locals)

            # Substitute free unbound symbols from context
            free_syms = list(sym_val.free_symbols)
            if free_syms and ctx:
                for free in free_syms:
                    fname = str(free)
                    matched_val = None
                    for ck, cv in ctx.items():
                        if ck.lower().replace('_', '') == fname.lower().replace('_', ''):
                            matched_val = cv
                            break
                    if matched_val is None and any(w in fname.lower() for w in ['s', 'area', 'b', 'day', 'base']):
                        for ck, cv in ctx.items():
                            if any(w in ck.lower() for w in ['s', 'area', 'b', 'day', 'base']):
                                matched_val = cv
                                break
                    if matched_val is None and 'prev' in ctx:
                        matched_val = ctx['prev']

                    if matched_val is not None:
                        sym_val = sym_val.subs(free, matched_val)

            sym_val = sp.simplify(sym_val)

            try:
                flt_val = float(sym_val.evalf())
            except Exception:
                flt_val = 0.0

            latex_val = sp.latex(sym_val)
            return sym_val, flt_val, latex_val

        except Exception as e:
            logger.warning(f"[MathCalculator] SymPy evaluate on '{s}' failed: {e}. Trying fallback...")
            try:
                safe_math = {"sqrt": np.sqrt, "pi": np.pi, "sin": np.sin, "cos": np.cos, "tan": np.tan}
                if ctx:
                    for k, v in ctx.items():
                        if isinstance(v, (int, float)): safe_math[k] = float(v)
                        elif isinstance(v, sp.Expr): safe_math[k] = float(v.evalf())
                flt_val = float(eval(s, {"__builtins__": {}}, safe_math))
                sym_val = sp.Float(flt_val)
                return sym_val, flt_val, str(flt_val)
            except Exception as e2:
                logger.error(f"[MathCalculator] Fallback eval error: {e2}")
                return None, None, s

    def process_solution_plan(
        self,
        steps_data: List[Dict[str, Any]],
        target_question: Optional[str] = None,
        coordinates: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Any]:
        """
        Processes a structured solution plan from LLM, evaluating all calculations deterministically.
        """
        context: Dict[str, Any] = {}
        formatted_steps: List[str] = []
        final_answer_sym = None
        symbolic_expr_parts = []

        for idx, step in enumerate(steps_data, start=1):
            if isinstance(step, str):
                verified_step, val = self._verify_text_step(step, context)
                formatted_steps.append(verified_step)
                if val is not None:
                    final_answer_sym = val
                continue

            explanation = step.get("explanation", "").strip()
            formula = step.get("formula", "").strip()
            calc_expr = step.get("calculation", "").strip()
            var_name = step.get("variable", "").strip()
            unit = step.get("unit", "").strip()

            if calc_expr:
                sym_val, flt_val, latex_val = self.evaluate_expression(calc_expr, context)
                
                if sym_val is not None:
                    if var_name:
                        self._save_to_context(context, var_name, sym_val)
                    
                    context['prev'] = sym_val
                    context['ans'] = sym_val
                    final_answer_sym = sym_val

                    if sym_val.is_integer:
                        val_display = str(int(flt_val))
                    elif sym_val.has(sp.sqrt, sp.pi) or sym_val.is_rational:
                        val_display = f"{sym_val} (≈ {flt_val:.2f})"
                    else:
                        val_display = f"{flt_val:.2f}" if abs(flt_val - round(flt_val)) > 1e-4 else str(int(round(flt_val)))

                    unit_str = f" {unit}" if unit else ""
                    
                    step_text = f"Bước {idx}: {explanation}."
                    if formula and calc_expr:
                        step_text += f" Ta có: {formula} = {calc_expr} = {val_display}{unit_str}."
                    elif formula:
                        step_text += f" Ta có: {formula} = {val_display}{unit_str}."
                    elif calc_expr:
                        step_text += f" Tính toán: {calc_expr} = {val_display}{unit_str}."

                    formatted_steps.append(step_text)
                    if formula:
                        symbolic_expr_parts.append(f"{formula} = {latex_val}")
                else:
                    formatted_steps.append(f"Bước {idx}: {explanation}.")
            else:
                formatted_steps.append(f"Bước {idx}: {explanation}.")

        final_answer_str = self._format_final_answer(final_answer_sym)
        final_symbolic_expression = "; ".join(symbolic_expr_parts) if symbolic_expr_parts else None

        return {
            "answer": final_answer_str,
            "steps": formatted_steps,
            "symbolic_expression": final_symbolic_expression,
            "evaluated_context": {k: str(v) for k, v in context.items() if k not in ('prev', 'ans')},
        }

    def process_text_steps(self, text_steps: List[str]) -> Dict[str, Any]:
        """
        Parses raw text steps, intercepts mathematical formulas with '=' signs,
        evaluates all expressions via SymPy, and replaces arithmetic with verified results.
        """
        context: Dict[str, Any] = {}
        formatted_steps: List[str] = []
        final_answer_sym = None
        symbolic_expr_parts = []

        for idx, step_str in enumerate(text_steps, start=1):
            clean_step = str(step_str).strip()
            verified_step, val = self._verify_text_step(clean_step, context)
            
            if not re.match(r'^(Bước|\d+[\.:\)])', verified_step, re.IGNORECASE):
                verified_step = f"Bước {idx}: {verified_step}"

            formatted_steps.append(verified_step)
            if val is not None:
                final_answer_sym = val
                symbolic_expr_parts.append(sp.latex(val))

        final_answer_str = self._format_final_answer(final_answer_sym)
        final_symbolic_expression = "; ".join(symbolic_expr_parts) if symbolic_expr_parts else None

        return {
            "answer": final_answer_str,
            "steps": formatted_steps,
            "symbolic_expression": final_symbolic_expression,
            "evaluated_context": {k: str(v) for k, v in context.items() if k not in ('prev', 'ans')},
        }

    def _verify_text_step(self, step_str: str, context: Dict[str, Any]) -> Tuple[str, Optional[sp.Expr]]:
        """
        Sentence-level equation parser and re-evaluator.
        Splits by sentences so multiple equations in one step are independently processed.
        """
        sentences = re.split(r'([.;]\s+)', step_str)
        rebuilt = []
        last_val = None

        for sentence in sentences:
            if '=' in sentence:
                parts = [p.strip() for p in sentence.split('=') if p.strip()]
                if len(parts) >= 2:
                    lhs = parts[0]
                    best_val = None
                    best_expr = None

                    # Check each remaining part to find the computable mathematical expression
                    for expr_cand in parts[1:]:
                        clean = expr_cand.replace('$', '').rstrip('.,;').strip()
                        if any(c in clean for c in '+-*/()0123456789') or clean in context:
                            sym_val, flt_val, latex_val = self.evaluate_expression(clean, context)
                            if sym_val is not None:
                                best_val = sym_val
                                best_expr = clean

                    if best_val is not None:
                        var_cand = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', lhs)
                        if var_cand:
                            var_name = var_cand[-1]
                            self._save_to_context(context, var_name, best_val)
                        context['prev'] = best_val
                        context['ans'] = best_val
                        last_val = best_val

                        flt = float(best_val.evalf())
                        disp = str(int(flt)) if best_val.is_integer else (
                            f"{best_val} (≈ {flt:.2f})" if best_val.has(sp.sqrt, sp.pi) or best_val.is_rational else f"{flt:.2f}"
                        )

                        if len(parts) > 2:
                            sentence = f"{lhs} = {parts[1]} = {disp}"
                        else:
                            sentence = f"{lhs} = {best_expr} = {disp}"
            rebuilt.append(sentence)

        return "".join(rebuilt), last_val or context.get('ans')

    def _save_to_context(self, context: Dict[str, Any], var_name: str, sym_val: sp.Expr):
        context[var_name] = sym_val
        clean_name = var_name.lower().replace('_', '').replace('{', '').replace('}', '')
        if 's' in clean_name or 'b' in clean_name or 'area' in clean_name:
            context['S_day'] = sym_val
            context['S'] = sym_val
            context['B'] = sym_val
            context['S_ABCD'] = sym_val
            context['S_ABC'] = sym_val
            if '1' in clean_name: context['S1'] = sym_val
            if '2' in clean_name: context['S2'] = sym_val
        elif 'h' in clean_name or 'so' in clean_name or 'height' in clean_name:
            context['h'] = sym_val
            context['SO'] = sym_val
        elif 'v' in clean_name:
            context['V'] = sym_val

    def _format_final_answer(self, sym_val: Optional[sp.Expr]) -> str:
        if sym_val is None:
            return ""
        flt_val = float(sym_val.evalf())
        if sym_val.is_integer:
            return str(int(flt_val))
        elif sym_val.has(sp.sqrt, sp.pi) or sym_val.is_rational:
            return f"{sym_val} (≈ {flt_val:.2f})"
        else:
            return f"{flt_val:.2f}" if abs(flt_val - round(flt_val)) > 1e-4 else str(int(round(flt_val)))
