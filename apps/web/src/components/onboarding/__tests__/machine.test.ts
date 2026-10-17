import { describe, expect, it } from "vitest";

import type { OnboardingState } from "@/lib/api";

import {
  FINALE,
  defaultPaperName,
  heardChips,
  hydrate,
  normaliseParsed,
  initialDraft,
  progress,
  reducer,
  stepPayload,
  topicsStillNeeded,
  type Action,
  type Draft,
  type Parsed,
} from "../machine";

const base = initialDraft({ displayName: "Abdul Rafe", timezone: "Asia/Karachi" });

function run(draft: Draft, ...actions: Action[]): Draft {
  return actions.reduce(reducer, draft);
}

const PARSED: Parsed = {
  topics: [{ slug: "ai", weight: 0.9 }],
  keywords: ["AI agents", "PSL"],
  entities: { people: [], companies: ["Anthropic"], teams: [], places: [] },
  blocked: { topics: ["film-tv"], keywords: ["celebrity gossip"] },
  context: "Runs an agency",
};

describe("defaults", () => {
  it("names the paper after the reader's first name", () => {
    expect(defaultPaperName("Abdul Rafe")).toBe("The Abdul Morning");
    expect(defaultPaperName("   ")).toBe("The Reader Morning");
    expect(base).toMatchObject({ step: 1, paperName: "The Abdul Morning", paperNameEdited: false, surpriseMe: true });
  });
});

describe("moving between steps", () => {
  it("advances from the name step once it has a name", () => {
    expect(reducer(base, { type: "next" }).step).toBe(2);
    const blank = run(base, { type: "set_name", paperName: "   " });
    expect(reducer(blank, { type: "next" }).step).toBe(1);
  });

  it("needs three topics before leaving the beats step", () => {
    const onBeats = { ...base, step: 2 };
    const two = run(onBeats, { type: "toggle_topic", slug: "ai" }, { type: "toggle_topic", slug: "f1" });
    expect(topicsStillNeeded(two)).toBe(1);
    expect(reducer(two, { type: "next" }).step).toBe(2);
    const three = run(two, { type: "toggle_topic", slug: "cricket" });
    expect(topicsStillNeeded(three)).toBe(0);
    expect(reducer(three, { type: "next" }).step).toBe(3);
  });

  it("goes back, but never into or out of the finale", () => {
    expect(reducer({ ...base, step: 3 }, { type: "back" }).step).toBe(2);
    expect(reducer(base, { type: "back" }).step).toBe(1);
    expect(reducer({ ...base, step: FINALE }, { type: "back" }).step).toBe(FINALE);
    expect(reducer({ ...base, step: FINALE }, { type: "next" }).step).toBe(FINALE);
  });

  it("only jumps to steps already reached", () => {
    const at4 = { ...base, step: 4 };
    expect(reducer(at4, { type: "goto", step: 2 }).step).toBe(2);
    expect(reducer(at4, { type: "goto", step: 5 }).step).toBe(4);
    expect(reducer(at4, { type: "goto", step: 0 }).step).toBe(4);
  });

  it("words, taste and reading can always be passed", () => {
    for (const step of [3, 4, 5]) expect(reducer({ ...base, step }, { type: "next" }).step).toBe(step + 1);
  });
});

describe("naming", () => {
  it("remembers that the reader chose the name", () => {
    const named = run(base, { type: "set_name", paperName: "The Lahore Ledger" });
    expect(named).toMatchObject({ paperName: "The Lahore Ledger", paperNameEdited: true });
  });
});

describe("beats", () => {
  it("toggles topics and drops their sub-interests when unpicked", () => {
    const d = run(
      base,
      { type: "toggle_topic", slug: "cricket" },
      { type: "toggle_deeper", slug: "cricket", label: "PSL" },
      { type: "toggle_deeper", slug: "cricket", label: "Test cricket" },
    );
    expect(d.deeper).toEqual({ cricket: ["PSL", "Test cricket"] });
    expect(run(d, { type: "toggle_deeper", slug: "cricket", label: "PSL" }).deeper).toEqual({
      cricket: ["Test cricket"],
    });
    expect(run(d, { type: "toggle_topic", slug: "cricket" })).toMatchObject({ topics: [], deeper: {} });
  });

  it("ignores sub-interests of topics that are not picked", () => {
    expect(run(base, { type: "toggle_deeper", slug: "f1", label: "Ferrari" })).toBe(base);
  });
});

describe("in their own words", () => {
  it("clears the reading of the text when the text changes", () => {
    const d = run({ ...base, text: "hello", parsed: PARSED }, { type: "set_text", text: "hello world" });
    expect(d.parsed).toBeNull();
    const same = { ...base, text: "hello", parsed: PARSED };
    expect(reducer(same, { type: "set_text", text: "hello" })).toBe(same);
  });

  it("splits the parsed result into heard and not chips", () => {
    const { heard, not } = heardChips(PARSED);
    expect(heard.map((c) => c.value)).toEqual(["ai", "AI agents", "PSL", "Anthropic"]);
    expect(not.map((c) => c.value)).toEqual(["film-tv", "celebrity gossip"]);
  });

  it("removes chips and adds keywords", () => {
    let d: Draft = { ...base, parsed: PARSED };
    d = run(
      d,
      { type: "remove_chip", chip: { kind: "topic", value: "ai" } },
      { type: "remove_chip", chip: { kind: "keyword", value: "PSL" } },
      { type: "remove_chip", chip: { kind: "entity", group: "companies", value: "Anthropic" } },
      { type: "remove_chip", chip: { kind: "blocked_topic", value: "film-tv" } },
      { type: "remove_chip", chip: { kind: "blocked_keyword", value: "celebrity gossip" } },
    );
    expect(d.parsed).toMatchObject({
      topics: [],
      keywords: ["AI agents"],
      entities: { companies: [] },
      blocked: { topics: [], keywords: [] },
    });
    d = run(d, { type: "add_keyword", keyword: "  F1 " }, { type: "add_keyword", keyword: "f1" }, { type: "add_keyword", keyword: " " });
    expect(d.parsed?.keywords).toEqual(["AI agents", "F1"]);
  });

  it("can add a keyword before anything was parsed", () => {
    expect(run(base, { type: "add_keyword", keyword: "chess" }).parsed?.keywords).toEqual(["chess"]);
  });
});

describe("normaliseParsed", () => {
  it("fills in what the API leaves out", () => {
    expect(normaliseParsed(null)).toBeNull();
    expect(normaliseParsed({ keywords: ["a"], context: "" })).toEqual({
      topics: [],
      keywords: ["a"],
      entities: { people: [], companies: [], teams: [], places: [] },
      blocked: { topics: [], keywords: [] },
      context: "",
    });
  });
});

describe("autosave payloads", () => {
  it("builds the body the API expects for each step", () => {
    const d: Draft = {
      ...base,
      paperName: "  The Rafe Morning ",
      city: " Lahore ",
      topics: ["ai", "cricket", "f1"],
      deeper: { cricket: ["PSL"] },
      text: " I follow AI ",
      parsed: PARSED,
      answers: { a: true, b: false },
      readingMinutes: 20,
      depth: "deep",
      surpriseMe: false,
    };
    expect(stepPayload(d, 1)).toEqual({ paper_name: "The Rafe Morning", city: "Lahore", timezone: "Asia/Karachi" });
    expect(stepPayload({ ...d, city: " " }, 1)).toMatchObject({ city: null });
    expect(stepPayload(d, 2)).toEqual({ topics: ["ai", "cricket", "f1"], deeper: { cricket: ["PSL"] } });
    expect(stepPayload(d, 3)).toEqual({ text: "I follow AI", parsed: PARSED });
    expect(stepPayload(d, 4)).toEqual({ answered: 2 });
    expect(stepPayload(d, 5)).toEqual({ reading_minutes: 20, depth: "deep", surprise_me: false });
    expect(stepPayload(d, FINALE)).toBeNull();
  });
});

describe("resuming", () => {
  const saved: OnboardingState = {
    step: 4,
    completed: false,
    name: { paper_name: "The Rafe Morning", city: "Lahore", timezone: "Europe/London" },
    beats: { topics: ["ai", "cricket", "f1"], deeper: { cricket: ["PSL"] } },
    words: { text: "AI and cricket", parsed: PARSED },
    reading: { reading_minutes: 5, depth: "brief", surprise_me: false },
    answers: { a: true },
  };

  it("restores everything that was saved", () => {
    expect(hydrate(base, saved)).toMatchObject({
      step: 4,
      paperName: "The Rafe Morning",
      paperNameEdited: true,
      city: "Lahore",
      timezone: "Europe/London",
      topics: ["ai", "cricket", "f1"],
      deeper: { cricket: ["PSL"] },
      text: "AI and cricket",
      parsed: PARSED,
      answers: { a: true },
      readingMinutes: 5,
      depth: "brief",
      surpriseMe: false,
    });
  });

  it("keeps the defaults for steps not saved yet", () => {
    const fresh: OnboardingState = { step: 1, completed: false, answers: {} };
    expect(hydrate(base, fresh)).toEqual(base);
  });

  it("lands on the finale for a finished reader", () => {
    expect(hydrate(base, { ...saved, step: 6, completed: true }).step).toBe(FINALE);
  });
});

describe("progress", () => {
  it("grows with the step and never passes one", () => {
    const values = [1, 2, 3, 4, 5, 6].map((step) => progress({ ...base, step }));
    expect(values).toEqual([...values].sort((a, b) => a - b));
    expect(values[0]).toBeGreaterThan(0);
    expect(values.at(-1)).toBeLessThanOrEqual(1);
  });
});
