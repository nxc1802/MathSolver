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
 * - Detects equations like "S_ABCD = a**2 = 36", "a^2 = 36", "SO = 12"
 * - Converts standalone powers like "a^2", "AB^2" outside equations
 * - Formats angles "60°" -> "$60^\circ$"
 * - Replaces raw point names like S_prime, SS_prime in text.
 */
export function formatMathMarkdown(text: string): string {
  if (!text || typeof text !== "string") return "";

  let result = text;

  // 1. Geometric point references in text (e.g. S_prime -> S', SS_prime -> SS', S_primeB -> S'B)
  result = result.replace(/\b([A-Z])_prime([A-Z])\b/g, "$1'$2");
  result = result.replace(/\b([A-Z])([A-Z])_prime\b/g, "$1$2'");
  result = result.replace(/\b([A-Z])_prime\b/g, "$1'");

  const mathBlocks: string[] = [];

  // 2. Extract existing $...$ math blocks
  result = result.replace(/\$([^$]+)\$/g, (_match, inner) => {
    const idx = mathBlocks.length;
    mathBlocks.push(`$${formatFormulaToLatex(inner)}$`);
    return `___MATH_BLOCK_${idx}___`;
  });

  // 3. Extract multi-part equality equations: "S_ABCD = a**2 = 36" or "AC'^2 = AC^2 + CC'^2 = 25 + 5^2 = 50"
  result = result.replace(
    /(?:Áp dụng công thức:\s*)?([A-Za-z0-9_'\.\{\}\\\^\(\)]+)\s*=\s*([^=;\n]+?)\s*=\s*([0-9\.\+\-\*\/\\sqrt\{\}a-zA-Z_'\^\s\(\)]+)(?=[,\.\s]|$)/g,
    (_match, lhs, expr, val) => {
      const formattedLhs = formatFormulaToLatex(lhs);
      const formattedExpr = formatFormulaToLatex(expr);
      const formattedVal = formatFormulaToLatex(val);
      const idx = mathBlocks.length;
      mathBlocks.push(`$${formattedLhs} = ${formattedExpr} = ${formattedVal}$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );

  // 4. Extract two-part equality equations: "V = (1/3) * S_day * h", "a^2 = 36", "SO = 12", "AC' = sqrt(50)"
  result = result.replace(
    /(?:Áp dụng công thức:\s*)?([A-Za-z0-9_'\.\{\}\\\^\(\)]+)\s*=\s*([0-9\.\+\-\*\/\\sqrt\{\}a-zA-Z_'\^\s\(\)]+)(?=[,\.\s]|$)/g,
    (_match, lhs, expr) => {
      const formattedLhs = formatFormulaToLatex(lhs);
      const formattedExpr = formatFormulaToLatex(expr);
      const idx = mathBlocks.length;
      mathBlocks.push(`$${formattedLhs} = ${formattedExpr}$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );

  // 5. In plain text, format standalone power terms: "a^2", "AB^2", "4^2", "SO^2", "x^3"
  result = result.replace(
    /\b([a-zA-Z][a-zA-Z0-9']{0,3}|\d+)\^(\d+|[a-zA-Z]+)\b/g,
    (_match, p1, p2) => {
      const idx = mathBlocks.length;
      mathBlocks.push(`$${p1}^{${p2}}$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );
  result = result.replace(
    /\b([a-zA-Z][a-zA-Z0-9']{0,3}|\d+)\*\*(\d+)\b/g,
    (_match, p1, p2) => {
      const idx = mathBlocks.length;
      mathBlocks.push(`$${p1}^{${p2}}$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );

  // 6. In plain text, format standalone subscripts: "S_ABCD", "V_SABCD", "h_prime"
  result = result.replace(
    /\b([A-Z])_([A-Za-z0-9]+)\b/g,
    (_match, p1, p2) => {
      const idx = mathBlocks.length;
      mathBlocks.push(`$${p1}_{${p2}}$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );
  result = result.replace(
    /\b([a-z])_prime\b/g,
    (_match, p1) => {
      const idx = mathBlocks.length;
      mathBlocks.push(`$${p1}'$`);
      return `___MATH_BLOCK_${idx}___`;
    }
  );

  // 7. In plain text, format angles: "60°", "30^\circ"
  result = result.replace(
    /(?:\b|\s)(\d+)\s*(?:\^\\circ|\\circ|°)/g,
    (_match, p1) => {
      const idx = mathBlocks.length;
      mathBlocks.push(`$${p1}^\\circ$`);
      return ` ___MATH_BLOCK_${idx}___`;
    }
  );

  // 8. In plain text, format standalone LaTeX commands: "\sqrt{50}", "\frac{1}{2}"
  result = result.replace(/\\sqrt\{([^}]+)\}/g, (_match, p1) => {
    const idx = mathBlocks.length;
    mathBlocks.push(`$\\sqrt{${p1}}$`);
    return `___MATH_BLOCK_${idx}___`;
  });
  result = result.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, (_match, p1, p2) => {
    const idx = mathBlocks.length;
    mathBlocks.push(`$\\frac{${p1}}{${p2}}$`);
    return `___MATH_BLOCK_${idx}___`;
  });

  // 9. Restore all math blocks
  result = result.replace(/___MATH_BLOCK_(\d+)___/g, (match, idx) => {
    return mathBlocks[Number(idx)] || match;
  });

  return result;
}
