/**
 * The onboarding step state machine: a pure reducer plus the rules for when a step is
 * complete and what to autosave. No React and no network, so it is trivially testable.
 */
import type { OnboardingState, ParsedInterests, StepBody } from "@/lib/api";

export const STEP_NAMES = ["name", "beats", "words", "taste", "reading", "finale"] as const;
export type StepName = (typeof STEP_NAMES)[number];
export const FINALE = STEP_NAMES.length;
export const MIN_TOPICS = 3;

/** ParsedInterests with every list present (the API omits empty defaults from its schema). */
export type Parsed = {
  topics: { slug: string; weight: number }[];
  keywords: string[];
  entities: { people: string[]; companies: string[]; teams: string[]; places: string[] };
  blocked: { topics: string[]; keywords: string[] };
  context: string;
};

export function normaliseParsed(raw: ParsedInterests | null | undefined): Parsed | null {
  if (!raw) return null;
  return {
    topics: raw.topics ?? [],
    keywords: raw.keywords ?? [],
    entities: {
      people: raw.entities?.people ?? [],
      companies: raw.entities?.companies ?? [],
      teams: raw.entities?.teams ?? [],
      places: raw.entities?.places ?? [],
    },
    blocked: { topics: raw.blocked?.topics ?? [], keywords: raw.blocked?.keywords ?? [] },
    context: raw.context ?? "",
  };
}

export type Depth = "brief" | "balanced" | "deep";
export type ReadingMinutes = 5 | 10 | 20;

export type Draft = {
  /** 1-based, like the API's step numbers */
  step: number;
  paperName: string;
  /** True once the reader typed a name, so we stop deriving it from their first name */
  paperNameEdited: boolean;
  city: string;
  timezone: string;
  topics: string[];
  deeper: Record<string, string[]>;
  text: string;
  parsed: Parsed | null;
  /** Taste test answers by article id; true = interested */
  answers: Record<string, boolean>;
  tasteTotal: number;
  readingMinutes: ReadingMinutes;
  depth: Depth;
  surpriseMe: boolean;
};

export type Action =
  | { type: "next" }
  | { type: "back" }
  | { type: "goto"; step: number }
  | { type: "set_name"; paperName: string }
  | { type: "set_city"; city: string }
  | { type: "set_timezone"; timezone: string }
  | { type: "toggle_topic"; slug: string }
  | { type: "toggle_deeper"; slug: string; label: string }
  | { type: "set_text"; text: string }
  | { type: "set_parsed"; parsed: Parsed | null }
  | { type: "remove_chip"; chip: Chip }
  | { type: "add_keyword"; keyword: string }
  | { type: "answer"; articleId: string; interested: boolean }
  | { type: "set_taste_total"; total: number }
  | { type: "set_reading"; minutes: ReadingMinutes }
  | { type: "set_depth"; depth: Depth }
  | { type: "set_surprise"; on: boolean };

export type Chip =
  | { kind: "topic"; value: string }
  | { kind: "keyword"; value: string }
  | { kind: "entity"; group: "people" | "companies" | "teams" | "places"; value: string }
  | { kind: "blocked_topic"; value: string }
  | { kind: "blocked_keyword"; value: string };

export function isValidTimeZone(timeZone: string): boolean {
  try {
    new Intl.DateTimeFormat("en-GB", { timeZone });
    return timeZone.length > 0;
  } catch {
    return false;
  }
}

export function defaultPaperName(displayName: string): string {
  const first = displayName.trim().split(/\s+/)[0] || "Reader";
  return `The ${first} Morning`;
}

export function initialDraft(defaults: { displayName: string; timezone: string; city?: string | null }): Draft {
  return {
    step: 1,
    paperName: defaultPaperName(defaults.displayName),
    paperNameEdited: false,
    city: defaults.city ?? "",
    timezone: defaults.timezone,
    topics: [],
    deeper: {},
    text: "",
    parsed: null,
    answers: {},
    tasteTotal: 0,
    readingMinutes: 10,
    depth: "balanced",
    surpriseMe: true,
  };
}

/** Rebuild the draft from what the API saved, so a refresh resumes exactly where it stopped. */
export function hydrate(draft: Draft, saved: OnboardingState): Draft {
  return {
    ...draft,
    step: Math.min(Math.max(saved.step, 1), FINALE),
    paperName: saved.name?.paper_name ?? draft.paperName,
    paperNameEdited: saved.name ? true : draft.paperNameEdited,
    city: saved.name?.city ?? draft.city,
    timezone: saved.name?.timezone ?? draft.timezone,
    topics: saved.beats?.topics ?? draft.topics,
    deeper: saved.beats?.deeper ?? draft.deeper,
    text: saved.words?.text ?? draft.text,
    parsed: saved.words ? normaliseParsed(saved.words.parsed) : draft.parsed,
    answers: saved.answers ?? {},
    readingMinutes: saved.reading?.reading_minutes ?? draft.readingMinutes,
    depth: saved.reading?.depth ?? draft.depth,
    surpriseMe: saved.reading?.surprise_me ?? draft.surpriseMe,
  };
}

function toggled(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function removeFrom(parsed: Parsed, chip: Chip): Parsed {
  switch (chip.kind) {
    case "topic":
      return { ...parsed, topics: parsed.topics.filter((t) => t.slug !== chip.value) };
    case "keyword":
      return { ...parsed, keywords: parsed.keywords.filter((k) => k !== chip.value) };
    case "entity":
      return {
        ...parsed,
        entities: { ...parsed.entities, [chip.group]: parsed.entities[chip.group].filter((e) => e !== chip.value) },
      };
    case "blocked_topic":
      return { ...parsed, blocked: { ...parsed.blocked, topics: parsed.blocked.topics.filter((t) => t !== chip.value) } };
    case "blocked_keyword":
      return {
        ...parsed,
        blocked: { ...parsed.blocked, keywords: parsed.blocked.keywords.filter((k) => k !== chip.value) },
      };
  }
}

export const EMPTY_PARSED: Parsed = {
  topics: [],
  keywords: [],
  entities: { people: [], companies: [], teams: [], places: [] },
  blocked: { topics: [], keywords: [] },
  context: "",
};

export function reducer(draft: Draft, action: Action): Draft {
  switch (action.type) {
    case "next":
      return canAdvance(draft) ? { ...draft, step: Math.min(draft.step + 1, FINALE) } : draft;
    case "back":
      // the finale has no way back: the paper is already being printed
      return draft.step > 1 && draft.step < FINALE ? { ...draft, step: draft.step - 1 } : draft;
    case "goto":
      return action.step >= 1 && action.step <= draft.step ? { ...draft, step: action.step } : draft;
    case "set_name":
      return { ...draft, paperName: action.paperName, paperNameEdited: true };
    case "set_city":
      return { ...draft, city: action.city };
    case "set_timezone":
      return { ...draft, timezone: action.timezone };
    case "toggle_topic": {
      const topics = toggled(draft.topics, action.slug);
      const deeper = { ...draft.deeper };
      if (!topics.includes(action.slug)) delete deeper[action.slug];
      return { ...draft, topics, deeper };
    }
    case "toggle_deeper": {
      if (!draft.topics.includes(action.slug)) return draft;
      const chosen = toggled(draft.deeper[action.slug] ?? [], action.label);
      const deeper = { ...draft.deeper };
      if (chosen.length) deeper[action.slug] = chosen;
      else delete deeper[action.slug];
      return { ...draft, deeper };
    }
    case "set_text":
      // editing the words makes the earlier reading of them stale
      return action.text === draft.text ? draft : { ...draft, text: action.text, parsed: null };
    case "set_parsed":
      return { ...draft, parsed: action.parsed };
    case "remove_chip":
      return draft.parsed ? { ...draft, parsed: removeFrom(draft.parsed, action.chip) } : draft;
    case "add_keyword": {
      const keyword = action.keyword.trim().slice(0, 80);
      const parsed = draft.parsed ?? EMPTY_PARSED;
      if (!keyword || parsed.keywords.some((k) => k.toLowerCase() === keyword.toLowerCase())) return draft;
      return { ...draft, parsed: { ...parsed, keywords: [...parsed.keywords, keyword] } };
    }
    case "answer":
      return { ...draft, answers: { ...draft.answers, [action.articleId]: action.interested } };
    case "set_taste_total":
      return { ...draft, tasteTotal: action.total };
    case "set_reading":
      return { ...draft, readingMinutes: action.minutes };
    case "set_depth":
      return { ...draft, depth: action.depth };
    case "set_surprise":
      return { ...draft, surpriseMe: action.on };
  }
}

/** Whether the reader may leave the current step forward. */
export function canAdvance(draft: Draft): boolean {
  switch (draft.step) {
    case 1:
      return draft.paperName.trim().length > 0 && isValidTimeZone(draft.timezone);
    case 2:
      return draft.topics.length >= MIN_TOPICS;
    case 3:
      // words are optional, but once typed they should be read so the chips can be checked
      return draft.text.trim() === "" || draft.parsed !== null;
    default:
      // taste and reading have sensible defaults, and the finale is the end
      return draft.step < FINALE;
  }
}

export function topicsStillNeeded(draft: Draft): number {
  return Math.max(0, MIN_TOPICS - draft.topics.length);
}

/** What to autosave when leaving `step`; null for steps that save nothing (the finale). */
export function stepPayload(draft: Draft, step: number): StepBody | null {
  switch (step) {
    case 1:
      return { paper_name: draft.paperName.trim(), city: draft.city.trim() || null, timezone: draft.timezone };
    case 2:
      return { topics: draft.topics, deeper: draft.deeper };
    case 3:
      return { text: draft.text.trim(), parsed: draft.parsed };
    case 4:
      return { answered: Math.min(Object.keys(draft.answers).length, 50) };
    case 5:
      return { reading_minutes: draft.readingMinutes, depth: draft.depth, surprise_me: draft.surpriseMe };
    default:
      return null;
  }
}

/** 0..1 for the progress bar: the step you are on counts as half done. */
export function progress(draft: Draft): number {
  return Math.min(1, (draft.step - 0.5) / FINALE);
}

/** "We heard" / "Not" chips, flattened for display. */
export function heardChips(parsed: Parsed): { heard: Chip[]; not: Chip[] } {
  const heard: Chip[] = [
    ...parsed.topics.map((t): Chip => ({ kind: "topic", value: t.slug })),
    ...parsed.keywords.map((value): Chip => ({ kind: "keyword", value })),
    ...(["people", "companies", "teams", "places"] as const).flatMap((group) =>
      parsed.entities[group].map((value): Chip => ({ kind: "entity", group, value })),
    ),
  ];
  const not: Chip[] = [
    ...parsed.blocked.topics.map((value): Chip => ({ kind: "blocked_topic", value })),
    ...parsed.blocked.keywords.map((value): Chip => ({ kind: "blocked_keyword", value })),
  ];
  return { heard, not };
}
