import { describe, expect, it } from "vitest";

import type { EditionItem } from "@/lib/api";

import {
  FRONT_PAGE,
  frontPage,
  initialStates,
  reduceStates,
  relativeTime,
  sectionsOf,
  sourceCount,
  unreadCount,
  visibleItems,
} from "../model";

let n = 0;
function item(over: Partial<EditionItem> = {}): EditionItem {
  n += 1;
  return {
    id: `item-${n}`,
    article_id: `article-${n}`,
    section: "Tech",
    position: n,
    slot: "standard",
    headline: `Headline ${n}`,
    summary: `Summary ${n}`,
    key_facts: [],
    why_text: null,
    url: `https://example.com/${n}`,
    source: "The Wire",
    image_url: null,
    published_at: null,
    score: 0.5,
    score_breakdown: {},
    state: { read: false, saved: false, skipped: false, reaction: null },
    ...over,
  };
}

describe("sectionsOf", () => {
  it("follows the composer's section order and sorts stories by position", () => {
    const a = item({ section: "Sport", position: 3 });
    const b = item({ section: "Tech", position: 2 });
    const c = item({ section: "Sport", position: 1 });
    const sections = sectionsOf({
      items: [a, b, c],
      layout: { sections: [{ name: "Tech" }, { name: "Sport" }] },
    });
    expect(sections.map((s) => s.name)).toEqual(["Tech", "Sport"]);
    expect(sections[1].items).toEqual([c, a]);
  });

  it("adds sections the layout forgot and drops empty ones", () => {
    const sections = sectionsOf({
      items: [item({ section: "Odd one" })],
      layout: { sections: [{ name: "Empty" }] },
    });
    expect(sections.map((s) => s.name)).toEqual(["Odd one"]);
  });
});

describe("item states", () => {
  const a = item();
  const b = item();

  it("starts from what the server says", () => {
    const states = initialStates([item({ state: { read: true, saved: true, skipped: false, reaction: "more" } })]);
    expect(Object.values(states)[0].saved).toBe(true);
  });

  it("marks stories read, saves, skips and reacts without touching the others", () => {
    let states = initialStates([a, b]);
    states = reduceStates(states, { type: "read", ids: [a.id] });
    states = reduceStates(states, { type: "save", id: a.id, on: true });
    states = reduceStates(states, { type: "react", id: b.id, reaction: "less" });
    states = reduceStates(states, { type: "skip", id: b.id, on: true });
    expect(states[a.id]).toEqual({ read: true, saved: true, skipped: false, reaction: null });
    expect(states[b.id]).toEqual({ read: false, saved: false, skipped: true, reaction: "less" });
    states = reduceStates(states, { type: "skip", id: b.id, on: false });
    expect(states[b.id].skipped).toBe(false);
  });

  it("counts unread stories, ignoring read and skipped ones", () => {
    let states = initialStates([a, b]);
    expect(unreadCount([a, b], states)).toBe(2);
    states = reduceStates(states, { type: "read", ids: [a.id] });
    states = reduceStates(states, { type: "skip", id: b.id, on: true });
    expect(unreadCount([a, b], states)).toBe(0);
  });
});

describe("visibleItems", () => {
  const tech = item({ section: "Tech", headline: "Agents everywhere" });
  const sport = item({ section: "Sport", headline: "Babar bats", source: "Dawn" });
  const skipped = item({ section: "Sport", headline: "Hidden" });
  const edition = { items: [tech, sport, skipped], layout: {} };
  const sections = sectionsOf(edition);
  const states = reduceStates(initialStates(edition.items), { type: "skip", id: skipped.id, on: true });

  it("shows one section, or everything on the front page, without skipped stories", () => {
    expect(visibleItems(sections, "Sport", states, "")).toEqual([sport]);
    expect(visibleItems(sections, FRONT_PAGE, states, "")).toEqual([tech, sport]);
  });

  it("searches headline, summary and source across every section", () => {
    expect(visibleItems(sections, "Tech", states, "babar")).toEqual([sport]);
    expect(visibleItems(sections, "Tech", states, "DAWN")).toEqual([sport]);
    expect(visibleItems(sections, "Tech", states, "nothing like this")).toEqual([]);
  });
});

describe("frontPage", () => {
  it("puts the lead first and sorts the rest into slots", () => {
    const lead = item({ slot: "lead" });
    const feature = item({ slot: "feature" });
    const brief = item({ slot: "brief" });
    const explore = item({ slot: "explore" });
    const page = frontPage([brief, feature, lead, explore]);
    expect(page.lead).toBe(lead);
    expect(page.features).toEqual([feature]);
    expect(page.briefs).toEqual([brief]);
    expect(page.explore).toEqual([explore]);
  });

  it("falls back to the first story when nothing is marked lead", () => {
    const first = item({ slot: "standard" });
    expect(frontPage([first, item()]).lead).toBe(first);
    expect(frontPage([]).lead).toBeNull();
  });
});

describe("helpers", () => {
  const now = new Date("2026-10-17T12:00:00Z");

  it("formats relative times", () => {
    expect(relativeTime("2026-10-17T11:59:40Z", now)).toBe("just now");
    expect(relativeTime("2026-10-17T11:15:00Z", now)).toBe("45m ago");
    expect(relativeTime("2026-10-17T07:00:00Z", now)).toBe("5h ago");
    expect(relativeTime("2026-10-15T12:00:00Z", now)).toBe("2d ago");
    expect(relativeTime("2026-09-01T12:00:00Z", now)).toBe("1 Sept");
    expect(relativeTime(null, now)).toBe("");
  });

  it("counts sources from the edition stats, or from the stories", () => {
    expect(sourceCount({ items: [], stats: { sources: 23 } })).toBe(23);
    expect(sourceCount({ items: [item({ source: "A" }), item({ source: "A" }), item({ source: "B" })], stats: {} })).toBe(2);
  });
});
