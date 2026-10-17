export type CardVariant = "lead" | "feature" | "standard" | "brief" | "explore";

/** What a card needs to render one story (mapped from an EditionItem + Article later). */
export type CardArticle = {
  id: string;
  headline: string;
  url: string;
  source: string;
  summary?: string;
  author?: string;
  /** ISO 8601 timestamp */
  publishedAt?: string;
  readingMinutes?: number;
  imageUrl?: string;
  /** Short reason this story was picked for the reader */
  why?: string;
  section?: string;
};
