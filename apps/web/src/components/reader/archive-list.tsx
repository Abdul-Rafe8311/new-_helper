"use client";

import { ArrowRight, Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api, pdfHref, type EditionSummary } from "@/lib/api";

import { useAccent, useActiveEdition } from "./chrome-context";
import { EditionHeader } from "./edition-header";
import { ARCHIVE_PAGE } from "./model";
import { FRONT_COLOR } from "./palette";
import { PageFrame } from "./page-frame";
import { SideNav } from "./side-nav";

function dayLabel(date: string): { weekday: string; rest: string } {
  const d = new Date(`${date}T12:00:00Z`);
  return {
    weekday: new Intl.DateTimeFormat("en-GB", { weekday: "long", timeZone: "UTC" }).format(d),
    rest: new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(d),
  };
}

/** Past editions, newest first, loading more as the reader scrolls. */
export function ArchiveList({ initial }: { initial: EditionSummary[] }) {
  const [editions, setEditions] = useState(initial);
  const [done, setDone] = useState(initial.length < ARCHIVE_PAGE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinel = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useActiveEdition(null);
  useAccent(FRONT_COLOR);

  const loadMore = useCallback(async () => {
    const last = editions.at(-1);
    if (busy.current || done || !last) return;
    busy.current = true;
    setLoading(true);
    setError(null);
    try {
      const page = await api.editions.list({ before: last.date, limit: ARCHIVE_PAGE });
      setEditions((current) => [...current, ...page]);
      if (page.length < ARCHIVE_PAGE) setDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load older editions.");
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }, [editions, done]);

  useEffect(() => {
    const element = sentinel.current;
    if (!element || done || error) return;
    const observer = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && void loadMore(), {
      rootMargin: "320px",
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [loadMore, done, error]);

  return (
    <PageFrame nav={<SideNav base="/today" />}>
      <EditionHeader title="Archive" dateLine="Every edition, as it was printed" />
      {editions.length === 0 ? (
        <p className="py-16 text-center font-sans text-xl font-bold">
          No past editions yet.
          <span className="mt-1 block text-base font-normal text-muted">They are filed here each morning.</span>
        </p>
      ) : (
        <ul aria-label="Past editions" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {editions.map((edition) => {
            const { weekday, rest } = dayLabel(edition.date);
            return (
              <li key={edition.id} className="story-card group relative">
                <div className="story-card__surface relative flex h-full min-h-[180px] flex-col rounded-[14px] border border-rule bg-surface p-5">
                  <p className="font-sans text-[13px] font-semibold tracking-wide text-muted uppercase">No. {edition.number}</p>
                  <h2 className="cta mt-1 font-sans text-2xl leading-tight font-extrabold tracking-tight">
                    <Link href={`/archive/${edition.date}`} prefetch={false} className="outline-none after:absolute after:inset-0 after:content-['']" data-story-link>
                      {weekday}
                      <span className="block text-base font-semibold text-muted">{rest}</span>
                    </Link>
                  </h2>
                  <p className="mt-2 font-sans text-sm text-muted">
                    {edition.item_count} {edition.item_count === 1 ? "story" : "stories"}
                  </p>
                  {edition.top_topics.length > 0 ? (
                    <ul className="mt-3 flex flex-wrap gap-1.5">
                      {edition.top_topics.slice(0, 3).map((topic) => (
                        <li key={topic} className="rounded-full bg-cat/10 px-2.5 py-0.5 font-sans text-xs font-semibold text-cat">
                          {topic}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="mt-auto flex items-center justify-between pt-4">
                    <span aria-hidden="true" className="cta inline-flex items-center gap-1 font-sans text-sm font-semibold">
                      Read <ArrowRight className="cta-arrow size-4" />
                    </span>
                    <a
                      href={pdfHref(edition.date)}
                      download
                      aria-label={`Download the PDF for ${edition.date}`}
                      title="Download PDF"
                      className="relative z-10 inline-flex size-10 items-center justify-center rounded-full text-muted outline-none hover:bg-paper-2 hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    >
                      <Download aria-hidden="true" className="size-4" />
                    </a>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <div ref={sentinel} aria-live="polite" className="py-8 text-center font-sans text-sm text-muted">
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 aria-hidden="true" className="size-4 animate-spin" /> Loading older editions…
          </span>
        ) : error ? (
          <span>
            <span role="alert" className="mr-3 text-destructive">
              {error}
            </span>
            <Button variant="outline" size="sm" onClick={() => void loadMore()}>
              Try again
            </Button>
          </span>
        ) : done && editions.length > 0 ? (
          "That's everything."
        ) : null}
      </div>
    </PageFrame>
  );
}
