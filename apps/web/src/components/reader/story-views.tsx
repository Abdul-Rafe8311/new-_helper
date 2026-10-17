"use client";

import { ArticleCard, Byline, SectionHeader, type CardArticle } from "@/components/paper";
import type { EditionItem } from "@/lib/api";
import { cn } from "@/lib/utils";

import { frontPage, relativeTime, stateOf, type ViewMode } from "./model";
import { Favicon, StoryDetail, StoryImage, StoryShell, UnreadDot } from "./story-parts";
import type { ReaderCore } from "./use-reader-core";

type ViewProps = { items: EditionItem[]; core: ReaderCore; now: Date };

function ListView({ items, core, now }: ViewProps) {
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {items.map((item) => {
        const state = stateOf(core.states, item.id);
        const expanded = core.expandedId === item.id;
        const detailId = `detail-${item.id}`;
        return (
          <li key={item.id}>
            <StoryShell item={item} state={state} focused={core.focusedId === item.id} className="px-1 py-2.5">
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={expanded ? detailId : undefined}
                onClick={() => core.toggleExpanded(item.id)}
                className="grid w-full grid-cols-[1.25rem_1fr_auto] items-center gap-x-3 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                <Favicon url={item.url} source={item.source} />
                <span className="min-w-0">
                  <span
                    className={cn(
                      "block truncate font-display text-base leading-snug",
                      state.read ? "font-medium text-muted" : "font-bold text-ink",
                    )}
                  >
                    {item.headline}
                  </span>
                  {!expanded && item.summary ? (
                    <span className="block truncate font-serif text-sm text-muted">{item.summary}</span>
                  ) : null}
                </span>
                <span className="flex items-center gap-2 font-sans text-xs text-muted">
                  <span className="hidden sm:inline">{item.source}</span>
                  <time dateTime={item.published_at ?? undefined}>{relativeTime(item.published_at, now)}</time>
                  <span className="w-2">
                    <UnreadDot unread={!state.read} />
                  </span>
                </span>
              </button>
              {expanded ? (
                <div className="pl-8">
                  <StoryDetail id={detailId} item={item} state={state} actions={core.actions} />
                </div>
              ) : null}
            </StoryShell>
          </li>
        );
      })}
    </ul>
  );
}

function CardsView({ items, core, now }: ViewProps) {
  return (
    <ul className="grid gap-x-6 gap-y-8 sm:grid-cols-2">
      {items.map((item, index) => {
        const state = stateOf(core.states, item.id);
        const expanded = core.expandedId === item.id;
        const detailId = `detail-${item.id}`;
        return (
          <li key={item.id} className={cn(expanded && "sm:col-span-2")}>
            <StoryShell
              item={item}
              state={state}
              focused={core.focusedId === item.id}
              className={cn("flex h-full flex-col data-[read=true]:opacity-80", expanded && "sm:flex-row sm:gap-6")}
            >
              <StoryImage
                item={item}
                priority={index === 0}
                sizes="(min-width: 640px) 50vw, 100vw"
                className={cn("mb-3 aspect-[16/9] w-full", expanded && "sm:mb-0 sm:aspect-[4/3] sm:w-2/5 sm:shrink-0")}
              />
              <div className="flex min-w-0 flex-1 flex-col">
                <p className="kicker mb-1 flex items-center gap-2 text-accent">
                  <UnreadDot unread={!state.read} />
                  {item.section}
                </p>
                <h3 className="font-display text-xl leading-snug font-bold text-ink">
                  <button
                    type="button"
                    aria-expanded={expanded}
                    aria-controls={expanded ? detailId : undefined}
                    onClick={() => core.toggleExpanded(item.id)}
                    className="text-left decoration-accent decoration-2 underline-offset-4 outline-none hover:underline focus-visible:underline"
                  >
                    {item.headline}
                  </button>
                </h3>
                {!expanded && item.summary ? (
                  <p className="mt-2 line-clamp-3 font-serif text-[0.95rem] leading-relaxed text-ink/90">
                    {item.summary}
                  </p>
                ) : null}
                <Byline
                  className="mt-2"
                  source={item.source}
                  publishedAt={item.published_at ?? undefined}
                />
                <p className="sr-only">{relativeTime(item.published_at, now)}</p>
                {expanded ? <StoryDetail id={detailId} item={item} state={state} actions={core.actions} /> : null}
              </div>
            </StoryShell>
          </li>
        );
      })}
    </ul>
  );
}

function asCard(item: EditionItem): CardArticle {
  return {
    id: item.id,
    headline: item.headline,
    url: item.url,
    source: item.source,
    summary: item.summary,
    publishedAt: item.published_at ?? undefined,
    imageUrl: item.image_url ?? undefined,
    why: item.why_text ?? undefined,
    section: item.section,
  };
}

function NewspaperStory({
  item,
  variant,
  core,
  className,
}: {
  item: EditionItem;
  variant: "lead" | "feature" | "standard" | "brief" | "explore";
  core: ReaderCore;
  className?: string;
}) {
  const state = stateOf(core.states, item.id);
  const expanded = core.expandedId === item.id;
  return (
    <StoryShell
      item={item}
      state={state}
      focused={core.focusedId === item.id}
      as="div"
      className={cn("data-[read=true]:opacity-80", className)}
    >
      <ArticleCard
        article={asCard(item)}
        variant={variant}
        breakdown={item.score_breakdown}
        onActivate={() => core.toggleExpanded(item.id)}
      >
        {expanded ? (
          <StoryDetail id={`detail-${item.id}`} item={item} state={state} actions={core.actions} />
        ) : null}
      </ArticleCard>
    </StoryShell>
  );
}

function NewspaperView({
  items,
  core,
  threeThings,
}: ViewProps & { threeThings: string[] }) {
  const page = frontPage(items);
  return (
    <div className="space-y-10">
      <div className="grid gap-x-8 gap-y-8 lg:grid-cols-12">
        {page.lead ? (
          <div className="lg:col-span-8">
            <NewspaperStory item={page.lead} variant="lead" core={core} />
          </div>
        ) : null}
        <aside className="space-y-6 lg:col-span-4 lg:border-l lg:border-rule lg:pl-6">
          {threeThings.length > 0 ? (
            <section aria-labelledby="three-things" className="border-2 border-ink p-4">
              <h2 id="three-things" className="kicker mb-2 text-accent">
                Three things to know
              </h2>
              <ol className="list-decimal space-y-2 pl-5 font-serif text-[0.95rem] leading-snug">
                {threeThings.slice(0, 3).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ol>
            </section>
          ) : null}
          {page.briefs.length > 0 ? (
            <section aria-labelledby="in-brief" className="space-y-3">
              <h2 id="in-brief" className="kicker">
                In brief
              </h2>
              {page.briefs.map((item) => (
                <NewspaperStory key={item.id} item={item} variant="brief" core={core} />
              ))}
            </section>
          ) : null}
        </aside>
      </div>

      {page.features.length > 0 ? (
        <div className="grid gap-x-8 gap-y-8 border-t border-rule pt-6 md:grid-cols-2 md:[&>*+*]:border-l md:[&>*+*]:border-rule md:[&>*+*]:pl-8">
          {page.features.map((item) => (
            <NewspaperStory key={item.id} item={item} variant="feature" core={core} />
          ))}
        </div>
      ) : null}

      {page.standards.length > 0 ? (
        <div className="grid gap-x-8 gap-y-8 border-t border-rule pt-6 sm:grid-cols-2 lg:grid-cols-3">
          {page.standards.map((item) => (
            <NewspaperStory key={item.id} item={item} variant="standard" core={core} />
          ))}
        </div>
      ) : null}

      {page.explore.length > 0 ? (
        <section className="space-y-4 border-t border-rule pt-6">
          <SectionHeader title="Outside your bubble" />
          <div className="grid gap-6 sm:grid-cols-2">
            {page.explore.map((item) => (
              <NewspaperStory key={item.id} item={item} variant="explore" core={core} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

/** The article pane in List, Cards or Newspaper form. */
export function StoryViews({
  view,
  items,
  core,
  now,
  threeThings = [],
  emptyMessage,
}: ViewProps & { view: ViewMode; threeThings?: string[]; emptyMessage: string }) {
  if (items.length === 0) {
    return <p className="py-16 text-center font-serif text-lg text-muted">{emptyMessage}</p>;
  }
  if (view === "list") return <ListView items={items} core={core} now={now} />;
  if (view === "newspaper") return <NewspaperView items={items} core={core} now={now} threeThings={threeThings} />;
  return <CardsView items={items} core={core} now={now} />;
}
