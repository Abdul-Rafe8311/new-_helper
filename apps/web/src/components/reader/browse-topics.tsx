"use client";

import { Check, Plus } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { SectionHeader } from "@/components/paper";
import type { CatalogueTopic, TopicCatalogue } from "@/lib/api";
import { cn } from "@/lib/utils";

import { ALL_SECTIONS, filterTopics } from "./catalogue-filter";
import { focusRing, pill } from "./interests-styles";

type Props = {
  catalogue: TopicCatalogue;
  /** Slugs that currently have a slider. */
  active: ReadonlySet<string>;
  /** Slugs the reader has blocked; they cannot be added until unblocked. */
  blocked: ReadonlySet<string>;
  onAdd: (topic: CatalogueTopic) => void;
  onRemove: (topic: CatalogueTopic) => void;
};

/** Search and section filters over the whole catalogue, with one real button per topic. */
export function BrowseTopics({ catalogue, active, blocked, onAdd, onRemove }: Props) {
  const searchId = useId();
  const [query, setQuery] = useState("");
  const [section, setSection] = useState(ALL_SECTIONS);
  const shown = useMemo(() => filterTopics(catalogue.topics, query, section), [catalogue.topics, query, section]);

  return (
    <section aria-labelledby="browse-h" className="mb-10">
      <SectionHeader title="Browse topics" description={`${catalogue.topics.length} to choose from`} />
      <h3 id="browse-h" className="sr-only">
        Browse topics
      </h3>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor={searchId} className="font-sans text-sm font-semibold">
            Search topics
          </label>
          <input
            id={searchId}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Try “chips”, “tennis” or “budget”"
            autoComplete="off"
            className={cn("h-11 w-full max-w-md rounded-md border border-rule bg-paper px-3 font-sans text-base", focusRing)}
          />
        </div>

        <div role="group" aria-label="Filter by section" className="flex flex-wrap gap-2">
          {[ALL_SECTIONS, ...catalogue.sections].map((name) => (
            <button
              key={name}
              type="button"
              aria-pressed={section === name}
              onClick={() => setSection(name)}
              className={cn(pill, section === name && "border-accent bg-accent/10")}
            >
              {name}
            </button>
          ))}
        </div>

        <p role="status" aria-live="polite" className="font-sans text-sm text-muted">
          {shown.length === 1 ? "1 topic" : `${shown.length} topics`}
        </p>

        {shown.length === 0 ? (
          <p className="font-serif text-muted">Nothing matches. Try another word or section.</p>
        ) : (
          <ul data-testid="catalogue-list" className="grid gap-x-10 sm:grid-cols-2">
            {shown.map((t) => {
              const on = active.has(t.slug);
              const isBlocked = blocked.has(t.slug);
              return (
                <li key={t.slug} className="flex items-center justify-between gap-3 border-b border-rule py-2">
                  <div className="min-w-0">
                    <p className="font-sans text-[15px] font-semibold">{t.label}</p>
                    <p className="font-serif text-sm leading-snug text-muted">{t.description}</p>
                  </div>
                  {isBlocked ? (
                    <span className="shrink-0 font-sans text-sm text-muted">Blocked</span>
                  ) : on ? (
                    <button
                      type="button"
                      aria-label={`Remove ${t.label}`}
                      onClick={() => onRemove(t)}
                      className={cn(pill, "shrink-0 border-accent bg-accent/10")}
                    >
                      <Check aria-hidden className="size-3.5" />
                      Added
                    </button>
                  ) : (
                    <button type="button" aria-label={`Add ${t.label}`} onClick={() => onAdd(t)} className={cn(pill, "shrink-0")}>
                      <Plus aria-hidden className="size-3.5" />
                      Add
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
