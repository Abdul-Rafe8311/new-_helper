/**
 * A stable colour per category, so a section looks the same every day. Deep enough that white text
 * on the card panel keeps >= 4.5:1 contrast. No image analysis: the palette is the whole system.
 */
export const PALETTE = [
  "#c8323a", // red
  "#c2561a", // orange
  "#8f6500", // gold
  "#23804f", // green
  "#0b7f8b", // teal
  "#2f5fd0", // blue
  "#4b49b8", // indigo
  "#7a3fb0", // violet
  "#b8337f", // pink
] as const;

/** The whole-paper colour ("For You"). */
export const FRONT_COLOR = "#2f5fd0";

export function categoryColor(name: string): string {
  let hash = 5381;
  for (const char of name.toLowerCase()) hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}
