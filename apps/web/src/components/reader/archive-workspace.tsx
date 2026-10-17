"use client";

import { Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { formatShortDate } from "@/components/paper";
import { Button } from "@/components/ui/button";
import { ApiError, api, pdfHref, type EditionSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

import { useChrome } from "./chrome-context";
import { ARCHIVE_PAGE } from "./model";
import { PanelLinks, PanelShell } from "./panel";

function weekday(date: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", timeZone: "UTC" }).format(new Date(`${date}T12:00:00Z`));
}

/** Past editions (newest first) that load more as the reader scrolls the panel. */
function EditionList({ initial }: { initial: EditionSummary[] }) {
  const pathname = usePathname();
  const { closeDrawer } = useChrome();
  const [editions, setEditions] = useState(initial);
  const [done, setDone] = useState(initial.length < ARCHIVE_PAGE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinel = useRef<HTMLLIElement>(null);
  const busy = useRef(false);

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
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) void loadMore();
      },
      { rootMargin: "240px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [loadMore, done, error]);

  if (editions.length === 0) {
    return <p className="font-serif text-sm text-muted">No past editions yet. They are filed here each morning.</p>;
  }

  return (
    <ul aria-label="Past editions" className="space-y-1">
      {editions.map((edition) => {
        const active = pathname === `/archive/${edition.date}`;
        return (
          <li key={edition.id} className={cn("group relative rounded-md", active ? "bg-paper-2" : "hover:bg-paper-2/70")}>
            <Link
              href={`/archive/${edition.date}`}
              prefetch={false}
              aria-current={active ? "page" : undefined}
              onClick={closeDrawer}
              className="block rounded-md px-2.5 py-2 pr-10 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <span className="block font-sans text-sm font-semibold">
                {weekday(edition.date)}, {formatShortDate(`${edition.date}T12:00:00Z`)}
              </span>
              <span className="block font-sans text-xs text-muted">
                No. {edition.number} · {edition.item_count} {edition.item_count === 1 ? "story" : "stories"}
              </span>
              {edition.top_topics.length > 0 ? (
                <span className="mt-1 flex flex-wrap gap-1">
                  {edition.top_topics.slice(0, 3).map((topic) => (
                    <span key={topic} className="rounded-full bg-accent/10 px-2 py-0.5 font-sans text-[0.65rem] text-accent">
                      {topic}
                    </span>
                  ))}
                </span>
              ) : null}
            </Link>
            <a
              href={pdfHref(edition.date)}
              download
              aria-label={`Download the PDF for ${edition.date}`}
              title="Download PDF"
              className="absolute top-2 right-2 inline-flex size-7 items-center justify-center rounded-md text-muted outline-none hover:bg-paper hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <Download aria-hidden="true" className="size-4" />
            </a>
          </li>
        );
      })}
      <li ref={sentinel} className="py-2 text-center font-sans text-xs text-muted" aria-live="polite">
        {loading ? (
          <span className="inline-flex items-center gap-1.5">
            <Loader2 aria-hidden="true" className="size-3.5 animate-spin" /> Loading older editions…
          </span>
        ) : error ? (
          <span className="space-y-1">
            <span role="alert" className="block text-destructive">
              {error}
            </span>
            <Button variant="outline" size="xs" onClick={() => void loadMore()}>
              Try again
            </Button>
          </span>
        ) : done ? (
          "That's everything."
        ) : null}
      </li>
    </ul>
  );
}

/** Archive: past editions on the left, the chosen edition in the main pane. */
export function ArchiveWorkspace({ initial, children }: { initial: EditionSummary[]; children: ReactNode }) {
  return (
    <div className="flex flex-1 items-stretch">
      <PanelShell label="Past editions">
        <div className="w-full p-4">
          <h2 className="kicker mb-3">Archive</h2>
          <EditionList initial={initial} />
          <PanelLinks />
        </div>
      </PanelShell>
      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}

/** What /archive shows before an edition is chosen. */
export function ArchiveEmpty() {
  const { setPanelOpen } = useChrome();
  return (
    <section className="mx-auto max-w-md flex-1 px-4 py-16 text-center">
      <h1 className="font-display text-3xl font-black">The archive</h1>
      <p className="mt-2 font-serif text-lg text-muted">Pick an earlier edition to read it again.</p>
      <Button className="mt-5 md:hidden" variant="outline" onClick={() => setPanelOpen(true)}>
        Show past editions
      </Button>
    </section>
  );
}
