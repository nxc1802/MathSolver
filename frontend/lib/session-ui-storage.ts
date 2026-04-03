const SPLIT_KEY = "mathsolver-split-percent";
const SIDEBAR_KEY = "mathsolver-sidebar-collapsed";

export function readSplitPercent(fallback: number): number {
  if (typeof window === "undefined") return fallback;
  try {
    const v = sessionStorage.getItem(SPLIT_KEY);
    if (v == null) return fallback;
    const n = parseFloat(v);
    if (Number.isNaN(n)) return fallback;
    return Math.min(50, Math.max(20, n));
  } catch {
    return fallback;
  }
}

export function writeSplitPercent(pct: number): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(SPLIT_KEY, String(pct));
  } catch {
    /* ignore quota */
  }
}

export function readSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return sessionStorage.getItem(SIDEBAR_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeSidebarCollapsed(collapsed: boolean): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
  } catch {
    /* ignore */
  }
}
