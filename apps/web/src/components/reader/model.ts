import type { Edition, EditionItem, ItemState } from "@/lib/api";

export type ViewMode = "list" | "cards" | "newspaper";
export const VIEW_MODES: readonly ViewMode[] = ["list", "cards", "newspaper"];
export const DEFAULT_VIEW: ViewMode = "cards";

/** The "all stories" pseudo-section: the whole front page. */
export const FRONT_PAGE = "";

/** How many editions the archive fetches at a time. */
export const ARCHIVE_PAGE = 20;

export type Reaction = "more" | "less";
export type ItemStates = Record<string, ItemState>;

export type Section = { name: string; items: EditionItem[] };

const BLANK: ItemState = { read: false, saved: false, skipped: false, reaction: null };

export function stateOf(states: ItemStates, id: string): ItemState {
  return states[id] ?? BLANK;
}

export function initialStates(items: readonly EditionItem[]): ItemStates {
  return Object.fromEntries(items.map((item) => [item.id, item.state]));
}

export type StateAction =
  | { type: "read"; ids: readonly string[] }
  | { type: "save"; id: string; on: boolean }
  | { type: "skip"; id: string; on: boolean }
  | { type: "react"; id: string; reaction: Reaction | null };

export function reduceStates(states: ItemStates, action: StateAction): ItemStates {
  switch (action.type) {
    case "read": {
      const next = { ...states };
      for (const id of action.ids) next[id] = { ...stateOf(states, id), read: true };
      return next;
    }
    case "save":
      return { ...states, [action.id]: { ...stateOf(states, action.id), saved: action.on } };
    case "skip":
      return { ...states, [action.id]: { ...stateOf(states, action.id), skipped: action.on } };
    case "react":
      return { ...states, [action.id]: { ...stateOf(states, action.id), reaction: action.reaction } };
  }
}

/** Sections in the order the composer laid them out; any item it forgot goes in by its own section. */
export function sectionsOf(edition: Pick<Edition, "items" | "layout">): Section[] {
  const declared = (edition.layout as { sections?: { name?: unknown }[] }).sections ?? [];
  const names: string[] = [];
  for (const entry of declared) {
    if (typeof entry.name === "string" && !names.includes(entry.name)) names.push(entry.name);
  }
  for (const item of edition.items) if (!names.includes(item.section)) names.push(item.section);
  return names
    .map((name) => ({
      name,
      items: edition.items.filter((item) => item.section === name).sort((a, b) => a.position - b.position),
    }))
    .filter((section) => section.items.length > 0);
}

/** Stories that are neither read nor skipped. */
export function unreadCount(items: readonly EditionItem[], states: ItemStates): number {
  return items.filter((item) => {
    const state = stateOf(states, item.id);
    return !state.read && !state.skipped;
  }).length;
}

export function readCount(items: readonly EditionItem[], states: ItemStates): number {
  return items.filter((item) => stateOf(states, item.id).read).length;
}

export function matchesQuery(item: EditionItem, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return [item.headline, item.summary, item.source, item.section].some((text) =>
    text.toLowerCase().includes(needle),
  );
}

/** What a view shows: the chosen section (or all), minus skipped stories, narrowed by search. */
export function visibleItems(
  sections: readonly Section[],
  section: string,
  states: ItemStates,
  query: string,
): EditionItem[] {
  const pool = query.trim() || section === FRONT_PAGE ? sections : sections.filter((s) => s.name === section);
  return pool
    .flatMap((s) => s.items)
    .filter((item) => !stateOf(states, item.id).skipped && matchesQuery(item, query));
}

export function sourceCount(edition: Pick<Edition, "items" | "stats">): number {
  const fromStats = Number((edition.stats as { sources?: unknown }).sources);
  return Number.isFinite(fromStats) && fromStats > 0 ? fromStats : new Set(edition.items.map((i) => i.source)).size;
}

export function threeThings(layout: Edition["layout"]): string[] {
  const raw = (layout as { three_things?: unknown }).three_things;
  return Array.isArray(raw) ? raw.filter((t): t is string => typeof t === "string") : [];
}

export type FrontPage = {
  lead: EditionItem | null;
  features: EditionItem[];
  standards: EditionItem[];
  briefs: EditionItem[];
  explore: EditionItem[];
};

/** Sort stories into the broadsheet's slots. With no lead slot, the first story leads. */
export function frontPage(items: readonly EditionItem[]): FrontPage {
  const bySlot = (slot: EditionItem["slot"]) => items.filter((i) => i.slot === slot);
  const leads = bySlot("lead");
  const lead = leads[0] ?? items[0] ?? null;
  const rest = items.filter((i) => i.id !== lead?.id);
  return {
    lead,
    features: rest.filter((i) => i.slot === "feature"),
    standards: rest.filter((i) => i.slot === "standard" || i.slot === "lead"),
    briefs: rest.filter((i) => i.slot === "brief"),
    explore: rest.filter((i) => i.slot === "explore"),
  };
}

export function relativeTime(iso: string | null | undefined, now: Date): string {
  if (!iso) return "";
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days < 7 ? `${days}d ago` : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(iso));
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}
