import type { CatalogueTopic } from "@/lib/api";

export const ALL_SECTIONS = "All";

/** Topics whose label or description contains every word typed, within one section or all. */
export function filterTopics(topics: CatalogueTopic[], query: string, section: string): CatalogueTopic[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return topics.filter((t) => {
    if (section !== ALL_SECTIONS && t.section !== section) return false;
    const haystack = `${t.label} ${t.description}`.toLowerCase();
    return words.every((w) => haystack.includes(w));
  });
}
