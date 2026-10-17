"use client";

import { Pin, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { SectionHeader } from "@/components/paper";
import { ApiError, api, type CatalogueTopic, type Interests, type SourceCatalogue, type Timeline, type TopicCatalogue } from "@/lib/api";
import { cn } from "@/lib/utils";

import { BrowseTopics } from "./browse-topics";
import { useAccent, useActiveEdition } from "./chrome-context";
import { EditionHeader } from "./edition-header";
import { focusRing, pill } from "./interests-styles";
import { FRONT_COLOR } from "./palette";
import { SourceToggles } from "./source-toggles";

const SAVE_DELAY_MS = 500;

/** "Saturday 17 October" for a local ISO day, without letting the browser's zone shift it. */
function dayLabel(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

type Props = { initial: Interests; initialTimeline: Timeline; topicCatalogue: TopicCatalogue; sourceCatalogue: SourceCatalogue };

/** "What Daybreak has learned about you": sliders, learned names, blocked topics, and the log. */
export function InterestsWorkspace({ initial, initialTimeline, topicCatalogue, sourceCatalogue }: Props) {
  useActiveEdition(null);
  useAccent(FRONT_COLOR);
  const [data, setData] = useState(initial);
  const [timeline, setTimeline] = useState(initialTimeline);
  const [drafts, setDrafts] = useState<Record<string, number>>({});
  const [confirmingReset, setConfirmingReset] = useState(false);
  // topics with a slider: those with weight at load, plus what the reader adds. Removing sets the weight to 0
  // and drops the slider; the history stays.
  const [active, setActive] = useState(() => new Set(initial.topics.filter((t) => t.weight > 0).map((t) => t.slug)));
  const [message, setMessage] = useState<string | null>(null);
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  useEffect(() => {
    const pending = timers.current;
    return () => Object.values(pending).forEach(clearTimeout);
  }, []);

  const refreshTimeline = useCallback(async () => {
    try {
      setTimeline(await api.interests.timeline());
    } catch {
      // the log is a convenience; keep what is on screen
    }
  }, []);

  const run = useCallback(
    async (action: () => Promise<Interests>, done?: string): Promise<Interests | null> => {
      try {
        const next = await action();
        setData(next);
        setMessage(done ?? null);
        await refreshTimeline();
        return next;
      } catch (error) {
        setMessage(error instanceof ApiError ? error.message : "That did not save. Try again.");
        return null;
      }
    },
    [refreshTimeline],
  );

  const moveSlider = (slug: string, label: string, weight: number) => {
    setDrafts((d) => ({ ...d, [slug]: weight }));
    clearTimeout(timers.current[slug]);
    timers.current[slug] = setTimeout(async () => {
      await run(() => api.interests.setTopics({ [slug]: weight }), `Saved ${label}.`);
      setDrafts((d) => Object.fromEntries(Object.entries(d).filter(([key]) => key !== slug)));
    }, SAVE_DELAY_MS);
  };

  const addTopic = async (topic: CatalogueTopic) => {
    const next = await run(() => api.interests.setTopics({ [topic.slug]: topicCatalogue.default_weight }), `Added ${topic.label}. Find its slider under Topics.`);
    if (next) setActive((a) => new Set(a).add(topic.slug));
  };

  const removeTopic = async (topic: CatalogueTopic) => {
    clearTimeout(timers.current[topic.slug]);
    setDrafts((d) => Object.fromEntries(Object.entries(d).filter(([key]) => key !== topic.slug)));
    const next = await run(() => api.interests.setTopics({ [topic.slug]: 0 }), `Removed ${topic.label}.`);
    if (next) setActive((a) => new Set([...a].filter((slug) => slug !== topic.slug)));
  };

  const toggleSource = (name: string, on: boolean) =>
    run(() => (on ? api.interests.unblockSource(name) : api.interests.blockSource(name)), `${on ? "Switched on" : "Switched off"} ${name}.`);

  const sliders = data.topics.filter((t) => active.has(t.slug));
  const hasTimeline = timeline.days.length > 0;

  return (
    <div className="max-w-5xl">
      <EditionHeader title="What Daybreak has learned about you" dateLine="Your interests" note="Everything here is yours to change. The paper listens to what you read, skip, save and rate." />
      <p role="status" aria-live="polite" className="min-h-6 pb-2 font-sans text-sm text-muted">
        {message}
      </p>

      {data.is_new && !hasTimeline ? (
        <section aria-labelledby="how-it-learns" className="mb-10 border-y border-rule py-5">
          <h2 id="how-it-learns" className="font-sans text-xl font-bold">
            How your paper learns
          </h2>
          <p className="mt-2 max-w-prose font-serif text-lg leading-relaxed text-muted">
            Open a story and it leans your way. Skip one and it backs off. Save it, or say “more like this” or “less like this”, and it takes
            note at once. Each night it tidies up what it noticed, and the changes appear below. Nothing has changed yet, so start reading.
          </p>
        </section>
      ) : null}

      <section aria-labelledby="topics-h" className="mb-10">
        <SectionHeader title="Topics" description="Drag to say how much you care" />
        <h3 id="topics-h" className="sr-only">
          Topic weights
        </h3>
        {sliders.length === 0 ? (
          <p className="font-serif text-muted">No topics yet. Add some below.</p>
        ) : (
          <ul className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
            {sliders.map((t) => {
              const value = drafts[t.slug] ?? t.weight;
              const id = `topic-${t.slug}`;
              return (
                <li key={t.slug} className="flex flex-col gap-1">
                  <label htmlFor={id} className="flex justify-between font-sans text-[15px] font-semibold">
                    <span>{t.label}</span>
                    <span className="text-muted tabular-nums">{Math.round(value * 100)}%</span>
                  </label>
                  <input
                    id={id}
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={Math.round(value * 100)}
                    aria-valuetext={`${Math.round(value * 100)} percent`}
                    onChange={(e) => moveSlider(t.slug, t.label, Number(e.target.value) / 100)}
                    className={cn("h-6 w-full cursor-pointer accent-accent", focusRing, "focus-visible:ring-offset-2")}
                  />
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <BrowseTopics
        catalogue={topicCatalogue}
        active={active}
        blocked={new Set(data.blocked.map((b) => b.topic))}
        onAdd={addTopic}
        onRemove={removeTopic}
      />

      <SourceToggles catalogue={sourceCatalogue} off={new Set(data.blocked_sources)} onToggle={toggleSource} />

      <section aria-labelledby="names-h" className="mb-10">
        <SectionHeader title="Names it follows" description="Pin one to keep it for good" />
        <h3 id="names-h" className="sr-only">
          Learned names
        </h3>
        {data.entities.length === 0 ? (
          <p className="font-serif text-muted">Nothing learned yet. Names appear once they keep turning up in stories you like.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {data.entities.map((e) => (
              <li key={e.id} className="inline-flex items-center gap-1">
                <button
                  type="button"
                  aria-pressed={e.pinned}
                  aria-label={`${e.pinned ? "Unpin" : "Pin"} ${e.name}`}
                  onClick={() => run(() => api.interests.pin(e.id, !e.pinned))}
                  className={cn(pill, e.pinned && "border-accent bg-accent/10")}
                >
                  <Pin aria-hidden className={cn("size-3.5", e.pinned && "fill-current")} />
                  {e.name}
                </button>
                <button
                  type="button"
                  aria-label={`Remove ${e.name}`}
                  onClick={() => run(() => api.interests.removeEntity(e.id), `Removed ${e.name}.`)}
                  className={cn("inline-flex size-9 items-center justify-center rounded-full text-muted hover:bg-paper-2 hover:text-ink", focusRing)}
                >
                  <X aria-hidden className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="blocked-h" className="mb-10">
        <SectionHeader title="Blocked topics" description="You will not see these" />
        <h3 id="blocked-h" className="sr-only">
          Blocked topics
        </h3>
        {data.blocked.length === 0 ? (
          <p className="font-serif text-muted">Nothing is blocked.</p>
        ) : (
          <ul data-testid="blocked-list" className="flex flex-col divide-y divide-rule border-y border-rule">
            {data.blocked.map((b) => (
              <li key={b.topic} className="flex items-center justify-between py-2">
                <span className="font-sans font-semibold">{b.label}</span>
                <button
                  type="button"
                  aria-label={`Unblock ${b.label}`}
                  onClick={() => run(() => api.interests.unblock(b.topic), `Unblocked ${b.label}.`)}
                  className={pill}
                >
                  Unblock
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="timeline-h" className="mb-10">
        <SectionHeader title="Recent changes" description="The last 30 days" />
        <h3 id="timeline-h" className="sr-only">
          Timeline of changes
        </h3>
        {hasTimeline ? (
          <ol data-testid="timeline" className="flex flex-col gap-6">
            {timeline.days.map((day) => (
              <li key={day.date}>
                <h4 className="font-sans text-sm font-bold tracking-wide text-muted uppercase">{dayLabel(day.date)}</h4>
                <ul className="mt-2 flex flex-col gap-1.5 border-l-2 border-rule pl-4">
                  {day.entries.map((entry) => (
                    <li key={entry.id} className="font-serif text-lg leading-snug">
                      {entry.text}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        ) : (
          <p className="font-serif text-muted">No changes yet.</p>
        )}
      </section>

      <section aria-labelledby="reset-h" className="mb-10">
        <SectionHeader title="Start over" />
        <h3 id="reset-h" className="sr-only">
          Reset
        </h3>
        {confirmingReset ? (
          <div role="group" aria-label="Confirm reset" className="flex flex-wrap items-center gap-3">
            <p className="font-serif text-lg">Forget the names it learned and return topics to what you chose at the start? The history stays.</p>
            <button
              type="button"
              onClick={async () => {
                const next = await run(() => api.interests.reset(), "Back to your starting interests.");
                if (next) setActive(new Set(next.topics.filter((t) => t.weight > 0).map((t) => t.slug)));
                setConfirmingReset(false);
              }}
              className={cn(pill, "border-accent bg-accent text-accent-ink hover:bg-accent/90")}
            >
              Yes, reset
            </button>
            <button type="button" onClick={() => setConfirmingReset(false)} className={pill}>
              Cancel
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => setConfirmingReset(true)} className={pill}>
            Reset what it has learned
          </button>
        )}
      </section>
    </div>
  );
}
