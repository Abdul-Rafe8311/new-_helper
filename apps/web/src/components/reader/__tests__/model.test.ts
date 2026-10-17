import { describe, expect, it } from "vitest";

import type { EditionItem } from "@/lib/api";

import { categoryColor, FRONT_COLOR, PALETTE } from "../palette";
import {
  applyPatches,
  outletCount,
  relativeTime,
  sectionFromParam,
  sectionsOf,
  slugify,
  spanFor,
  stateFor,
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

describe("sections", () => {
  it("follows the composer's order, sorts by position and gives each a unique slug", () => {
    const a = item({ section: "Sport", position: 3 });
    const b = item({ section: "Tech & AI", position: 2 });
    const c = item({ section: "Sport", position: 1 });
    const sections = sectionsOf({
      items: [a, b, c],
      layout: { sections: [{ name: "Tech & AI" }, { name: "Sport" }] },
    });
    expect(sections.map((s) => [s.name, s.slug])).toEqual([
      ["Tech & AI", "tech-and-ai"],
      ["Sport", "sport"],
    ]);
    expect(sections[1].items).toEqual([c, a]);
  });

  it("adds sections the layout forgot, drops empty ones and de-duplicates slugs", () => {
    const sections = sectionsOf({
      items: [item({ section: "A B" }), item({ section: "A-B" })],
      layout: { sections: [{ name: "Empty" }] },
    });
    expect(sections.map((s) => s.slug)).toEqual(["a-b", "a-b-2"]);
  });

  it("resolves ?section= and falls back to the whole paper", () => {
    const sections = sectionsOf({ items: [item({ section: "Sport" })], layout: {} });
    expect(sectionFromParam(sections, "sport")?.name).toBe("Sport");
    expect(sectionFromParam(sections, "nope")).toBeNull();
    expect(sectionFromParam(sections, null)).toBeNull();
    expect(slugify("  Hello, World!  ")).toBe("hello-world");
  });
});

describe("story state", () => {
  const a = item();
  const b = item({ state: { read: true, saved: false, skipped: false, reaction: null } });

  it("falls back to what the server sent until the reader changes something", () => {
    expect(stateFor({}, b).read).toBe(true);
    const next = applyPatches({}, [{ id: a.id, base: a.state, patch: { saved: true } }]);
    expect(stateFor(next, a)).toEqual({ read: false, saved: true, skipped: false, reaction: null });
    expect(stateFor(next, b)).toBe(b.state);
  });

  it("layers patches on the latest override, not the server state", () => {
    let states = applyPatches({}, [{ id: a.id, base: a.state, patch: { saved: true } }]);
    states = applyPatches(states, [{ id: a.id, base: a.state, patch: { reaction: "more" } }]);
    expect(stateFor(states, a)).toMatchObject({ saved: true, reaction: "more" });
  });

  it("counts unread stories and hides skipped ones", () => {
    const sections = sectionsOf({ items: [a, b], layout: {} });
    expect(unreadCount([a, b], {})).toBe(1);
    const skipped = applyPatches({}, [{ id: a.id, base: a.state, patch: { skipped: true } }]);
    expect(visibleItems(sections, null, skipped)).toEqual([b]);
    expect(unreadCount([a, b], skipped)).toBe(0);
    expect(visibleItems(sections, "tech", {})).toEqual([a, b]);
    expect(visibleItems(sections, "other", {})).toEqual([]);
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

  it("reports outlet counts only when the composer recorded more than one", () => {
    expect(outletCount({ score_breakdown: { cluster_size: 5 } })).toBe(5);
    expect(outletCount({ score_breakdown: { cluster_size: 1 } })).toBeNull();
    expect(outletCount({ score_breakdown: {} })).toBeNull();
  });

  it("lays rows out as 7+5, 4+4+4, 5+7, 4+4+4 and repeats", () => {
    expect(Array.from({ length: 10 }, (_, i) => spanFor(i))).toEqual([7, 5, 4, 4, 4, 5, 7, 4, 4, 4]);
    expect(spanFor(10)).toBe(7);
  });

  it("gives a category the same colour every day, from the palette", () => {
    expect(categoryColor("Pavilion End")).toBe(categoryColor("pavilion end"));
    expect(PALETTE).toContain(categoryColor("Markets"));
    expect(new Set(["Markets", "Science", "Pakistan", "Sport", "Culture"].map(categoryColor)).size).toBeGreaterThan(2);
    expect(PALETTE).toContain(FRONT_COLOR);
  });
});
