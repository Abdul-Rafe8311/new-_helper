import { describe, expect, it } from "vitest";

import type { CatalogueTopic } from "@/lib/api";

import { ALL_SECTIONS, filterTopics } from "../catalogue-filter";

const topics: CatalogueTopic[] = [
  { slug: "climate", label: "Climate & Environment", section: "Climate", description: "Climate change and conservation." },
  { slug: "cricket", label: "Cricket", section: "Sport", description: "Test, ODI and T20 cricket." },
  { slug: "tennis", label: "Tennis", section: "Sport", description: "Grand Slams and the ATP tour." },
];

describe("filterTopics", () => {
  it("returns everything for an empty query and the All section", () => {
    expect(filterTopics(topics, "  ", ALL_SECTIONS)).toHaveLength(3);
  });

  it("matches label and description words, ignoring case", () => {
    expect(filterTopics(topics, "CLIMATE", ALL_SECTIONS).map((t) => t.slug)).toEqual(["climate"]);
    expect(filterTopics(topics, "grand slams", ALL_SECTIONS).map((t) => t.slug)).toEqual(["tennis"]);
  });

  it("narrows to one section", () => {
    expect(filterTopics(topics, "", "Sport").map((t) => t.slug)).toEqual(["cricket", "tennis"]);
    expect(filterTopics(topics, "climate", "Sport")).toEqual([]);
  });
});
