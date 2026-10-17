import type { CardArticle } from "./types";

/** Sample stories for the styleguide and component tests. Not real articles. */
export const MOCK_ARTICLES: Record<"lead" | "feature" | "standard" | "brief" | "explore", CardArticle> = {
  lead: {
    id: "mock-lead",
    section: "World",
    headline: "Monsoon talks end with a rare deal on shared river data",
    summary:
      "After nine days of negotiation, delegates agreed to publish upstream flow readings every hour, a small technical step that could give downstream cities days of extra warning before floods.",
    url: "https://example.com/monsoon-deal",
    source: "The Example Times",
    author: "Sana Mir",
    publishedAt: "2026-10-17T01:10:00Z",
    readingMinutes: 6,
    why: "You follow climate and Pakistan",
  },
  feature: {
    id: "mock-feature",
    section: "Technology",
    headline: "Inside the lab teaching small models to check their own work",
    summary:
      "A team of eleven researchers thinks the next leap won't come from bigger models but from ones that know when they are wrong.",
    url: "https://example.com/self-checking-models",
    source: "Example Review",
    author: "Omar Farooq",
    publishedAt: "2026-10-16T18:30:00Z",
    readingMinutes: 9,
    why: "Matches your interest in AI research",
  },
  standard: {
    id: "mock-standard",
    section: "Sport",
    headline: "Lahore Qalandars name an uncapped spinner for the season opener",
    summary:
      "The 19-year-old took 31 wickets in domestic cricket last season and impressed in the nets against the touring side.",
    url: "https://example.com/qalandars-spinner",
    source: "Example Sports",
    publishedAt: "2026-10-16T22:05:00Z",
    readingMinutes: 3,
    why: "You follow Lahore Qalandars",
  },
  brief: {
    id: "mock-brief",
    headline: "Central bank holds rates steady for a third month",
    url: "https://example.com/rates",
    source: "Example Markets",
    readingMinutes: 1,
  },
  explore: {
    id: "mock-explore",
    headline: "The typeface designers reviving forgotten Urdu calligraphy styles",
    summary:
      "A small studio in Karachi is digitising nastaliq variants that disappeared with hot-metal printing.",
    url: "https://example.com/urdu-type",
    source: "Example Design",
    author: "Hira Baig",
    publishedAt: "2026-10-15T09:00:00Z",
    readingMinutes: 7,
    why: "Something new: design, near your interests",
  },
};
