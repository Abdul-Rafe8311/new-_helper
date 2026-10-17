import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { formatShortDate } from "./format";

type BylineProps = {
  source: string;
  author?: string;
  publishedAt?: string;
  readingMinutes?: number;
  className?: string;
};

/** "By Jane Doe · Dawn · 17 Oct · 4 min read" */
export function Byline({ source, author, publishedAt, readingMinutes, className }: BylineProps) {
  const parts: ReactNode[] = [];
  if (author) parts.push(<span key="author">By {author}</span>);
  parts.push(
    <span key="source" className="font-semibold text-ink">
      {source}
    </span>,
  );
  if (publishedAt) {
    parts.push(
      <time key="date" dateTime={publishedAt}>
        {formatShortDate(publishedAt)}
      </time>,
    );
  }
  if (readingMinutes) parts.push(<span key="read">{readingMinutes} min read</span>);

  return (
    <p className={cn("font-sans text-xs text-muted", className)}>
      {parts.map((part, i) => (
        <span key={i}>
          {i > 0 ? <span aria-hidden="true"> · </span> : null}
          {part}
        </span>
      ))}
    </p>
  );
}
