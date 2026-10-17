/**
 * A clearly labelled sample edition for the signed-out landing page. Nothing here is real news:
 * the headlines are written for NewsHelper and there are no photographs (previews use flat
 * section-coloured tiles). Counts below are counts of this fixture, nothing more.
 */
export type SampleStory = {
  id: string;
  section: string;
  headline: string;
  summary: string;
  source: string;
  sources: number;
  readMins: number;
};

export const SAMPLE_DATE = "Saturday 17 October 2026";

/** Earlier days of the sample archive. The fixture has no stories for them, so no counts are shown. */
export const SAMPLE_ARCHIVE_DATES: readonly string[] = [
  "Friday 16 October 2026",
  "Thursday 15 October 2026",
  "Wednesday 14 October 2026",
  "Tuesday 13 October 2026",
];

export const SAMPLE_SECTION_COLORS: Readonly<Record<string, string>> = {
  Technology: "#3fb5a8",
  Science: "#a7cc52",
  Business: "#f2b544",
  Music: "#b79ced",
};

export const SAMPLE_STORIES: readonly SampleStory[] = [
  {
    id: "lead",
    section: "Technology",
    headline: "Small on-device models start to change how phones read the news",
    summary: "Summaries that never leave your handset are becoming a standard feature, and readers notice the difference.",
    source: "Harbour Post",
    sources: 7,
    readMins: 4,
  },
  {
    id: "science",
    section: "Science",
    headline: "A new deep-sea survey maps hundreds of species no one had catalogued",
    summary: "Researchers combined sonar and sampling to chart a corner of the ocean floor in unusual detail.",
    source: "Fieldnotes Weekly",
    sources: 4,
    readMins: 6,
  },
  {
    id: "business",
    section: "Business",
    headline: "Regional bakeries report a steady rise in flour costs",
    summary: "Small producers say prices have crept up for three quarters in a row.",
    source: "Ledger & Loaf",
    sources: 3,
    readMins: 3,
  },
  {
    id: "music",
    section: "Music",
    headline: "Independent venues pair old classics with live bands",
    summary: "Sold-out evening shows are pulling younger audiences back into the room.",
    source: "The Evening Reel",
    sources: 2,
    readMins: 5,
  },
];
