"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, type MouseEvent } from "react";

import { originalHref, type Story } from "@/lib/api";

import { useAccent, useActiveEdition } from "./chrome-context";
import { FeedbackActions } from "./feedback-actions";
import { outletCount, relativeTime, stateFor } from "./model";
import { categoryColor } from "./palette";
import { PageFrame } from "./page-frame";
import { PhotoGallery } from "./photo-gallery";
import { PhotoStack } from "./photo-stack";
import { SideNav } from "./side-nav";
import { SourceList } from "./source-list";
import { UndoToast } from "./toast";
import { useItemActions } from "./use-item-actions";
import { useChrome } from "./chrome-context";

/** "Back to edition": a real link, upgraded to history-back so the feed keeps its scroll position. */
function BackLink({ href }: { href: string }) {
  const router = useRouter();
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    const fromFeed = window.history.length > 1 && document.referrer.startsWith(window.location.origin);
    if (!fromFeed) return;
    event.preventDefault();
    router.back();
  };
  return (
    <Link
      href={href}
      onClick={onClick}
      className="cta inline-flex min-h-10 items-center gap-2 rounded-full px-3 font-sans text-sm font-semibold text-muted outline-none hover:bg-cat/10 hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
    >
      <ArrowLeft aria-hidden="true" className="size-4" /> Back to edition
    </Link>
  );
}

export function StoryDetail({ story, now }: { story: Story; now: string }) {
  const { item } = story;
  const nowDate = useMemo(() => new Date(now), [now]);
  const color = categoryColor(item.section);
  const { states } = useChrome();
  const { actions, toast } = useItemActions("story");
  const state = stateFor(states, item);
  useAccent(color);
  useActiveEdition({ date: story.edition_date, ready: true });

  // Opening a story is reading it.
  useEffect(() => {
    actions.markRead([item], "story");
  }, [actions, item]);

  const outlets = outletCount(item);
  const age = relativeTime(item.published_at, nowDate);

  return (
    <PageFrame nav={<SideNav base={`/paper/${story.edition_date}`} />}>
      <div className="pt-1">
        <BackLink href={`/paper/${story.edition_date}`} />
      </div>

      <article>
        <header className="grid items-center gap-10 py-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:py-10">
          <div>
            <p className="font-sans text-[13px] font-semibold tracking-wide text-muted uppercase">
              <span className="text-cat">{item.section}</span> · {item.source}
              {age ? ` · ${age}` : ""}
              {outlets ? ` · ${outlets} outlets` : ""}
            </p>
            <h1 className="mt-3 font-display text-[clamp(2rem,4.6vw,3.75rem)] leading-[1.06] font-black tracking-tight text-balance">
              {item.headline}
            </h1>
            {story.author ? <p className="mt-3 font-sans text-sm text-muted">By {story.author}</p> : null}
            <div className="mt-6 flex flex-wrap items-center gap-2">
              <a
                href={originalHref(item.id)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => actions.opened(item)}
                className="cta press inline-flex h-10 items-center gap-2 rounded-full bg-cat px-5 font-sans text-sm font-semibold text-white outline-none hover:brightness-110 focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                Read original <ArrowRight aria-hidden="true" className="cta-arrow size-4" />
              </a>
              <PhotoGallery images={story.images} headline={item.headline} />
            </div>
            <FeedbackActions item={item} state={state} actions={actions} variant="labelled" className="mt-4" />
          </div>
          <PhotoStack images={story.images} />
        </header>

        <div className="grid gap-10 border-t border-rule pt-8 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="max-w-[70ch]">
            {item.summary ? (
              <section aria-labelledby="overview-heading">
                <h2 id="overview-heading" className="mb-3 font-sans text-sm font-bold tracking-wide text-muted uppercase">
                  Overview
                </h2>
                <p className="font-serif text-[1.15rem] leading-[1.75] text-ink">{item.summary}</p>
              </section>
            ) : null}
            {item.key_facts.length > 0 ? (
              <section aria-labelledby="facts-heading" className="mt-8">
                <h2 id="facts-heading" className="mb-3 font-sans text-sm font-bold tracking-wide text-muted uppercase">
                  Key facts
                </h2>
                <ul className="space-y-2 font-serif text-[1.05rem] leading-relaxed">
                  {item.key_facts.map((fact) => (
                    <li key={fact} className="flex gap-3">
                      <span aria-hidden="true" className="mt-2.5 size-1.5 shrink-0 rounded-full bg-cat" />
                      {fact}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {item.why_text ? (
              <p className="mt-8 border-l-2 border-cat pl-4 font-sans text-sm text-muted">
                <span className="font-semibold text-ink">Why it is in your paper: </span>
                {item.why_text}
              </p>
            ) : null}
          </div>
          <aside aria-label="Sources">
            <SourceList sources={story.sources} now={nowDate} />
          </aside>
        </div>
      </article>
      <UndoToast toast={toast.toast} onDismiss={toast.dismiss} />
    </PageFrame>
  );
}
