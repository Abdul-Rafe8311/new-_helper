/**
 * A clearly labelled sample edition for the signed-out landing page. Nothing here is real news:
 * the headlines are written for NewsHelper, and there are no images (cards fall back to a flat
 * section colour). `hoursAgo` is fixed so the static page never shows a stale clock.
 */
export type SampleStory = {
  id: string;
  section: string;
  headline: string;
  summary: string;
  sources: number;
  hoursAgo: number;
  /** Fictional outlet name, for the device preview only. */
  source: string;
  readMins: number;
};

export type SampleSection = { slug: string; label: string; color: string };

export const SAMPLE_SECTIONS: readonly SampleSection[] = [
  { slug: "technology", label: "Technology", color: "#5d7a74" },
  { slug: "science", label: "Science", color: "#7d8f5a" },
  { slug: "economics", label: "Economics", color: "#6b7048" },
  { slug: "culture", label: "Culture", color: "#8b6b78" },
] as const;

export const SAMPLE_STORIES: readonly SampleStory[] = [
  {
    id: "lead",
    source: "Harbour Post",
    readMins: 4,
    section: "technology",
    headline: "Small on-device models start to change how phones read the news",
    summary: "Summaries that never leave your handset are becoming a standard feature, and readers notice the difference.",
    sources: 7,
    hoursAgo: 3,
  },
  {
    id: "science",
    source: "Fieldnotes Weekly",
    readMins: 6,
    section: "science",
    headline: "A new deep-sea survey maps hundreds of species no one had catalogued",
    summary: "Researchers combined sonar and sampling to chart a corner of the ocean floor in unusual detail.",
    sources: 4,
    hoursAgo: 5,
  },
  {
    id: "economics",
    source: "Ledger & Loaf",
    readMins: 3,
    section: "economics",
    headline: "Regional bakeries report a steady rise in flour costs",
    summary: "Small producers say prices have crept up for three quarters in a row.",
    sources: 3,
    hoursAgo: 8,
  },
  {
    id: "culture",
    source: "The Evening Reel",
    readMins: 5,
    section: "culture",
    headline: "Independent cinemas pair old classics with live music",
    summary: "Sold-out evening screenings are pulling younger audiences back into the stalls.",
    sources: 2,
    hoursAgo: 12,
  },
];

export function sectionOf(slug: string): SampleSection {
  return SAMPLE_SECTIONS.find((s) => s.slug === slug) ?? SAMPLE_SECTIONS[0];
}

/** Two key facts for the story shown in the device preview's detail panel. */
export const SAMPLE_KEY_FACTS: readonly string[] = [
  "Seven outlets covered the story within three hours.",
  "Summaries run on the phone, so reading stays private.",
];

/** The phone preview's home screen: two sections, three small tiles each (titles are sample text). */
export const SAMPLE_PHONE_ROWS: readonly { section: string; tiles: readonly string[] }[] = [
  { section: "technology", tiles: ["On-device models", "Quiet chips", "Offline maps"] },
  { section: "science", tiles: ["Deep-sea survey", "Soil carbon", "Night-sky atlas"] },
];
