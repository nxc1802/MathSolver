/**
 * Math Formatting Utility for MathSolver
 * Automatically transforms raw Python/SymPy expressions, variable names with subscripts,
 * and arithmetic equations into clean, elegant KaTeX-compatible LaTeX Markdown.
 */

/**
 * Transforms variable names like S_ABCD, V_SABCD, h_prime, S_prime into LaTeX math notation.
 */
export function formatVariableName(varName: string): string {
  if (!varName) return "";
  let v = varName.trim();
  // V_S_prime_ADC -> V_{S'.ADC}
  v = v.replace(/^V_([A-Za-z]+)_prime_([A-Za-z]+)$/, "V_{$1'.$2}");
  // V_SABCD -> V_{S.ABCD}
  v = v.replace(/^V_([A-Z])([A-Z]+)$/, "V_{$1.$2}");
  // X_prime -> X'
  v = v.replace(/([A-Za-z]+)_prime/g, "$1'");
  // S_ABCD -> S_{ABCD}, S_day -> S_{đáy}, h_prime -> h'
  v = v.replace(/_([A-Za-z0-9]+)/g, "_{$1}");
  v = v.replace(/_\{day\}/g, "_{\\text{đáy}}");
  v = v.replace(/_\{xq\}/g, "_{\\text{xq}}");
  v = v.replace(/_\{tp\}/g, "_{\\text{tp}}");
  return v;
}

/**
 * Transforms a raw formula string (e.g. sp.Rational(1, 3) * S_ABCD * SO) into LaTeX.
 */
export function formatFormulaToLatex(formula: string): string {
  if (!formula) return "";
  let f = formula.trim();

  // sp.Rational(1, 3) or Rational(1, 3) -> \frac{1}{3}
  f = f.replace(/(?:sp\.)?Rational\((\d+),\s*(\d+)\)/g, "\\frac{$1}{$2}");

  // sp.sqrt(x) or sqrt(x) -> \sqrt{x}
  f = f.replace(/(?:sp\.)?sqrt\(([^)]+)\)/g, "\\sqrt{$1}");

  // pi -> \pi
  f = f.replace(/\b(?:sp\.)?pi\b/g, "\\pi");

  // Exponents: a**2 -> a^2, a**3 -> a^3
  f = f.replace(/\*\*(\d+|\w+)/g, "^$1");
  f = f.replace(/\*\*\(([^)]+)\)/g, "^{$1}");

  // Multiplications: * -> \cdot
  f = f.replace(/\s*\*\s*/g, " \\cdot ");

  // Points with _prime: S_prime -> S', A_prime -> A'
  f = f.replace(/([A-Za-z]+)_prime/g, "$1'");

  // Subscripts: S_ABCD -> S_{ABCD}, V_SABCD -> V_{S.ABCD}
  f = f.replace(/\bV_([A-Z])([A-Z]+)\b/g, "V_{$1.$2}");
  f = f.replace(/\b([A-Z])_([A-Za-z0-9]+)\b/g, "$1_{$2}");
  f = f.replace(/_\{day\}/g, "_{\\text{đáy}}");

  return f;
}

/**
 * Formats a full text line, step description, or markdown content:
 * - Detects formulas like "S_ABCD = a**2 = 36" or "h_prime = sp.Rational(1, 2) * SO = 6"
 *   and wraps them with proper $ ... $ LaTeX delimiters.
 * - Replaces raw point names like S_prime, SS_prime in text.
 */
export function formatMathMarkdown(text: string): string {
  if (!text || typeof text !== "string") return "";

  let result = text;

  // 1. Convert geometric point references in text (e.g. S_prime -> S', SS_prime -> SS', S_primeB -> S'B)
  result = result.replace(/\b([A-Z])_prime([A-Z])\b/g, "$1'$2");
  result = result.replace(/\b([A-Z])([A-Z])_prime\b/g, "$1$2'");
  result = result.replace(/\b([A-Z])_prime\b/g, "$1'");

  // 2. Pattern to detect equality formulas: e.g. "S_ABCD = a**2 = 36" or "V = sp.Rational(1, 3) * S * h = 144"
  // Match "Áp dụng công thức: X = Y = Z" or standalone equations
  result = result.replace(
    /(?:Áp dụng công thức:\s*)?([A-Za-z0-9_'\.\{\}\\]+)\s*=\s*([^=;\n]+?)\s*=\s*([0-9\.\+\-\*\/\\sqrt\{\}a-zA-Z_'\^]+)(?=[,\.\s]|$)/g,
    (match, lhs, expr, val) => {
      // If already wrapped in $, skip
      if (match.startsWith("$") && match.endsWith("$")) return match;
      const formattedLhs = formatVariableName(lhs);
      const formattedExpr = formatFormulaToLatex(expr);
      const formattedVal = formatFormulaToLatex(val);
      return `$${formattedLhs} = ${formattedExpr} = ${formattedVal}$`;
    }
  );

  // 3. Catch remaining two-part equations: "X = Y" with mathematical operators
  result = result.replace(
    /(?:Áp dụng công thức:\s*)?([A-Za-z0-9_'\.\{\}\\]+)\s*=\s*([^=;\n]+(?:\*|\/|\^|Rational|sqrt|\\frac|\\sqrt)[^=;\n]*)(?=[,\.\s]|$)/g,
    (match, lhs, expr) => {
      if (match.startsWith("$") && match.endsWith("$")) return match;
      const formattedLhs = formatVariableName(lhs);
      const formattedExpr = formatFormulaToLatex(expr);
      return `$${formattedLhs} = ${formattedExpr}$`;
    }
  );

  // 4. Standalone Python fragments like sp.Rational(1, 3) in text
  result = result.replace(/(?:sp\.)?Rational\((\d+),\s*(\d+)\)/g, "$\\frac{$1}{$2}$");
  result = result.replace(/(?:sp\.)?sqrt\(([^)]+)\)/g, "$\\sqrt{$1}$");

  return result;
}
