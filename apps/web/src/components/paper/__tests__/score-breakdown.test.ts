import { describe, expect, it } from "vitest";

import { explainScore } from "../score-breakdown";

describe("explainScore", () => {
  it("lists each weighted component largest first, in points out of 100", () => {
    const explained = explainScore({
      components: { semantic: 0.21, topic: 0.12, match: 0, recency: 0.08, importance: 0.03, novelty: 0.01 },
      penalties: { seen: 0.05 },
      total: 0.45,
      cluster_size: 6,
      terms: ["agents", "PSL"],
    });
    expect(explained).toEqual({
      total: 45,
      rows: [
        { key: "semantic", label: "Close to your interests", points: 21 },
        { key: "topic", label: "A topic you follow", points: 12 },
        { key: "recency", label: "Fresh", points: 8 },
        { key: "importance", label: "Widely covered", points: 3 },
        { key: "novelty", label: "Outside your usual beats", points: 1 },
      ],
      penalties: [{ key: "seen", label: "Seen before", points: 5 }],
      notes: ["Covered by 6 outlets", "Mentions agents, PSL"],
    });
  });

  it("has nothing to say when the story was not scored", () => {
    expect(explainScore({})).toBeNull();
    expect(explainScore(null)).toBeNull();
  });

  it("ignores malformed values", () => {
    const explained = explainScore({ components: { semantic: "high", topic: 0.1 }, total: "x" });
    expect(explained?.rows).toEqual([{ key: "topic", label: "A topic you follow", points: 10 }]);
    expect(explained?.total).toBe(0);
  });
});
