import { ArrowUpRight } from "lucide-react";

import type { StorySource } from "@/lib/api";

import { relativeTime } from "./model";

/** The outlets that covered the story; the first is the article this story was written from. */
export function SourceList({ sources, now }: { sources: StorySource[]; now: Date }) {
  if (sources.length === 0) return null;
  return (
    <section aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="mb-3 font-sans text-sm font-bold tracking-wide text-muted uppercase">
        {sources.length > 1 ? `Sources (${sources.length})` : "Source"}
      </h2>
      <ul className="space-y-3">
        {sources.map((source) => (
          <li key={source.url}>
            <a
              href={/^\/r\//.test(source.url) ? `/api${source.url}` : source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="cta group block rounded-xl border border-rule bg-surface p-4 outline-none transition-colors hover:border-cat/60 focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <span className="flex items-center justify-between gap-2 font-sans text-[13px] font-semibold text-muted">
                <span>
                  {source.name}
                  {source.published_at ? ` · ${relativeTime(source.published_at, now)}` : ""}
                </span>
                <ArrowUpRight aria-hidden="true" className="cta-arrow size-4" />
              </span>
              <span className="mt-1 block font-sans text-[15px] leading-snug font-bold text-ink">{source.title}</span>
              {source.primary ? <span className="mt-1.5 block font-sans text-xs text-cat">Read original</span> : null}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
