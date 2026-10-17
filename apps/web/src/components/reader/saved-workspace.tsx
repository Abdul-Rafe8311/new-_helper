"use client";

import { useCallback, useMemo, useState } from "react";

import { formatShortDate } from "@/components/paper";
import type { SavedItem } from "@/lib/api";

import { useActiveEdition, useChrome } from "./chrome-context";
import { initialStates, matchesQuery, stateOf, type ItemStates } from "./model";
import { PanelEntries, PanelLinks, PanelShell, type PanelEntry } from "./panel";
import { SectionTabs } from "./section-tabs";
import { StoryViews } from "./story-views";
import { UndoToast } from "./toast";
import { useReaderCore } from "./use-reader-core";

const ALL = "";

/** Saved stories from every edition, filterable by the day they ran. */
export function SavedWorkspace({ items, now }: { items: SavedItem[]; now: string }) {
  const { view, query, closeDrawer } = useChrome();
  const [day, setDay] = useState(ALL);
  const initial = useMemo(() => initialStates(items), [items]);
  const nowDate = useMemo(() => new Date(now), [now]);
  useActiveEdition(null);

  const choose = useCallback(
    (states: ItemStates) =>
      items.filter((item) => {
        const state = stateOf(states, item.id);
        return state.saved && !state.skipped && (day === ALL || item.edition_date === day) && matchesQuery(item, query);
      }),
    [items, day, query],
  );
  const core = useReaderCore(initial, view, choose);

  const saved = items.filter((item) => stateOf(core.states, item.id).saved);
  const days = [...new Set(saved.map((item) => item.edition_date))];
  const entries: PanelEntry[] = [
    { key: ALL, label: "All saved", count: saved.length },
    ...days.map((d) => ({
      key: d,
      label: formatShortDate(`${d}T12:00:00Z`),
      count: saved.filter((item) => item.edition_date === d).length,
    })),
  ];
  const select = (key: string) => {
    setDay(key);
    closeDrawer();
  };

  return (
    <div className="flex flex-1 items-stretch">
      <PanelShell label="Saved stories">
        <div className="w-full p-4">
          <h2 className="kicker mb-3">Saved</h2>
          <PanelEntries label="Saved by day" countLabel="saved" entries={entries} selected={day} onSelect={select} />
          <PanelLinks />
        </div>
      </PanelShell>
      <div className="min-w-0 flex-1 px-4 pt-4 pb-16 sm:px-6">
        <SectionTabs entries={entries} selected={day} onSelect={select} className="lg:hidden" />
        <header className="mt-4 mb-5">
          <h1 className="font-display text-3xl font-black tracking-tight sm:text-4xl">Saved</h1>
          <p className="mt-1 font-serif text-base text-muted italic">Stories you set aside to come back to.</p>
        </header>
        <StoryViews
          view={view}
          items={core.items}
          core={core}
          now={nowDate}
          emptyMessage={
            query.trim()
              ? "No saved story matches your search."
              : "Nothing saved yet. Press s on a story to keep it here."
          }
        />
      </div>
      <UndoToast toast={core.toast} onDismiss={core.dismissToast} />
    </div>
  );
}
