/** Turns the composer's `score_breakdown` JSON into rows a reader can understand. */

export type BreakdownRow = { key: string; label: string; points: number };

export type ScoreExplanation = {
  /** 0-100 */
  total: number;
  rows: BreakdownRow[];
  penalties: BreakdownRow[];
  /** e.g. "Covered by 6 outlets" */
  notes: string[];
};

const LABELS: Record<string, string> = {
  semantic: "Close to your interests",
  topic: "A topic you follow",
  match: "Names something you track",
  recency: "Fresh",
  importance: "Widely covered",
  novelty: "Outside your usual beats",
  seen: "Seen before",
  low_quality: "Lower-quality source",
};

const num = (value: unknown): number => (typeof value === "number" && Number.isFinite(value) ? value : 0);

function rowsOf(group: unknown): BreakdownRow[] {
  if (!group || typeof group !== "object") return [];
  return Object.entries(group as Record<string, unknown>)
    .map(([key, value]) => ({ key, label: LABELS[key] ?? key, points: Math.round(num(value) * 100) }))
    .filter((row) => row.points !== 0)
    .sort((a, b) => b.points - a.points);
}

/** Null when the story has no breakdown (e.g. an onboarding placeholder edition). */
export function explainScore(breakdown: Record<string, unknown> | null | undefined): ScoreExplanation | null {
  if (!breakdown || !("components" in breakdown)) return null;
  const notes: string[] = [];
  const cluster = num(breakdown.cluster_size);
  if (cluster > 1) notes.push(`Covered by ${cluster} outlets`);
  const terms = Array.isArray(breakdown.terms) ? breakdown.terms.filter((t): t is string => typeof t === "string") : [];
  if (terms.length) notes.push(`Mentions ${terms.join(", ")}`);
  return {
    total: Math.round(num(breakdown.total) * 100),
    rows: rowsOf(breakdown.components),
    penalties: rowsOf(breakdown.penalties),
    notes,
  };
}
