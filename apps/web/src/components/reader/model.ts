import type { Edition, EditionItem, ItemState } from "@/lib/api";

/** How many editions the archive fetches at a time. */
export const ARCHIVE_PAGE = 20;

export type Reaction = "more" | "less";

/**
 * The reader's own changes this visit (saved, skipped, ...), keyed by story. Stories the reader has
 * not touched fall back to the state the server sent with them, so this only holds overrides.
 */
export type ItemStates = Record<string, ItemState>;

export type StatePatch = { id: string; base: ItemState; patch: Partial<ItemState> };

export function stateFor(states: ItemStates, item: Pick<EditionItem, "id" | "state">): ItemState {
  return states[item.id] ?? item.state;
}

export function applyPatches(states: ItemStates, patches: readonly StatePatch[]): ItemStates {
  const next = { ...states };
  for (const { id, base, patch } of patches) next[id] = { ...(states[id] ?? base), ...patch };
  return next;
}

export type Section = { name: string; slug: string; items: EditionItem[] };

export function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "section"
  );
}

/** Sections in the order the composer laid them out; any item it forgot goes in by its own section. */
export function sectionsOf(edition: Pick<Edition, "items" | "layout">): Section[] {
  const declared = (edition.layout as { sections?: { name?: unknown }[] }).sections ?? [];
  const names: string[] = [];
  for (const entry of declared) {
    if (typeof entry.name === "string" && !names.includes(entry.name)) names.push(entry.name);
  }
  for (const item of edition.items) if (!names.includes(item.section)) names.push(item.section);
  const used = new Set<string>();
  return names
    .map((name) => {
      let slug = slugify(name);
      while (used.has(slug)) slug += "-2";
      used.add(slug);
      return {
        name,
        slug,
        items: edition.items.filter((item) => item.section === name).sort((a, b) => a.position - b.position),
      };
    })
    .filter((section) => section.items.length > 0);
}

/** Stories of one section (or all of them when `slug` is null), minus the ones the reader skipped. */
export function visibleItems(sections: readonly Section[], slug: string | null, states: ItemStates): EditionItem[] {
  const pool = slug === null ? sections : sections.filter((s) => s.slug === slug);
  return pool.flatMap((s) => s.items).filter((item) => !stateFor(states, item).skipped);
}

/** Which section a `?section=` value names; unknown values fall back to the whole paper. */
export function sectionFromParam(sections: readonly Section[], param: string | null): Section | null {
  return sections.find((s) => s.slug === param) ?? null;
}

export function unreadCount(items: readonly EditionItem[], states: ItemStates): number {
  return items.filter((item) => {
    const state = stateFor(states, item);
    return !state.read && !state.skipped;
  }).length;
}

/** The number of outlets covering a story, only when the composer recorded more than one. */
export function outletCount(item: Pick<EditionItem, "score_breakdown">): number | null {
  const n = Number((item.score_breakdown as { cluster_size?: unknown }).cluster_size);
  return Number.isFinite(n) && n > 1 ? n : null;
}

export function relativeTime(iso: string | null | undefined, now: Date): string {
  if (!iso) return "";
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days < 7
    ? `${days}d ago`
    : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(iso));
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/**
 * Column spans (out of 12) for the wide feed, one row's worth at a time: the lead row favours the
 * first story, later rows mix thirds and wider cards. Repeats, so any number of stories fills rows.
 */
export const ROW_SPANS: readonly (readonly number[])[] = [[7, 5], [4, 4, 4], [5, 7], [4, 4, 4]];

export function spanFor(index: number): number {
  const flat = ROW_SPANS.flat();
  return flat[index % flat.length];
}
