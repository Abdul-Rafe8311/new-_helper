"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { SectionHeader } from "@/components/paper";
import { api, type Taxonomy, type Topic } from "@/lib/api";

import { Chip } from "./chip";
import { MIN_TOPICS, topicsStillNeeded } from "./machine";
import { StepHeading } from "./step-heading";
import type { StepProps } from "./steps-props";

/** Sub-interests never change within a session, so they are fetched once per topic. */
const suggestionCache = new Map<string, string[]>();

export function BeatsStep({ draft, dispatch, taxonomy }: StepProps & { taxonomy: Taxonomy }) {
  const needed = topicsStillNeeded(draft);

  return (
    <section>
      <StepHeading
        step={2}
        title="Pick your beats"
        lede={`Choose at least ${MIN_TOPICS} topics. Tap one to go deeper.`}
        why="Your beats become the sections of your paper; going deeper tells us what to look for inside them."
      />

      <p
        role="status"
        className="sticky top-0 z-10 -mx-1 mb-4 bg-canvas/90 px-1 py-2 font-sans text-sm text-muted backdrop-blur"
      >
        {needed > 0 ? (
          <>
            <strong className="text-ink">{draft.topics.length}</strong> chosen. Pick {needed} more to continue.
          </>
        ) : (
          <>
            <strong className="text-ink">{draft.topics.length}</strong> chosen. You can add as many as you like.
          </>
        )}
      </p>

      <div className="space-y-8">
        {taxonomy.groups.map((group) => {
          const topics = taxonomy.topics.filter((t) => t.group === group);
          const picked = topics.filter((t) => draft.topics.includes(t.slug));
          return (
            <div key={group}>
              <SectionHeader title={group} />
              <div className="flex flex-wrap gap-2">
                {topics.map((topic) => (
                  <Chip
                    key={topic.slug}
                    size="lg"
                    selected={draft.topics.includes(topic.slug)}
                    onClick={() => dispatch({ type: "toggle_topic", slug: topic.slug })}
                  >
                    {topic.label}
                  </Chip>
                ))}
              </div>
              <AnimatePresence initial={false}>
                {picked.map((topic) => (
                  <GoDeeper
                    key={topic.slug}
                    topic={topic}
                    chosen={draft.deeper[topic.slug] ?? []}
                    onToggle={(label) => dispatch({ type: "toggle_deeper", slug: topic.slug, label })}
                  />
                ))}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function GoDeeper({
  topic,
  chosen,
  onToggle,
}: {
  topic: Topic;
  chosen: string[];
  onToggle: (label: string) => void;
}) {
  const reduceMotion = useReducedMotion();
  const [fetched, setFetched] = useState<string[] | "failed" | null>(null);
  const [attempt, setAttempt] = useState(0);
  const options = suggestionCache.get(topic.slug) ?? fetched;

  useEffect(() => {
    if (suggestionCache.has(topic.slug)) return;
    let cancelled = false;
    api.onboarding
      .suggestions(topic.slug)
      .then((r) => {
        suggestionCache.set(topic.slug, r.suggestions);
        if (!cancelled) setFetched(r.suggestions);
      })
      .catch(() => {
        if (!cancelled) setFetched("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [topic.slug, attempt]);

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.2 }}
      className="overflow-hidden"
    >
      <div className="mt-3 border-l-2 border-accent bg-paper-2/60 py-3 pr-3 pl-4" data-testid={`deeper-${topic.slug}`}>
        <p className="kicker mb-2 text-muted">Go deeper in {topic.label}</p>
        {Array.isArray(options) ? (
          <div className="flex flex-wrap gap-2">
            {options.map((label) => (
              <Chip key={label} selected={chosen.includes(label)} onClick={() => onToggle(label)}>
                {label}
              </Chip>
            ))}
          </div>
        ) : options === "failed" ? (
          <p className="font-sans text-sm text-muted">
            Couldn&apos;t load ideas.{" "}
            <button
              type="button"
              onClick={() => {
                setFetched(null);
                setAttempt((n) => n + 1);
              }}
              className="text-accent underline underline-offset-4"
            >
              Try again
            </button>
          </p>
        ) : (
          <div aria-label="Loading ideas" className="h-9 w-2/3 animate-pulse bg-paper-2" />
        )}
      </div>
    </motion.div>
  );
}
