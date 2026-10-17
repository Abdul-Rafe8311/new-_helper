"use client";

import { useCallback, useMemo, useState } from "react";

import { formatDateLine, Rule } from "@/components/paper";
import type { Edition } from "@/lib/api";

import { useActiveEdition, useChrome } from "./chrome-context";
import {
  FRONT_PAGE,
  initialStates,
  type ItemStates,
  readCount,
  sectionsOf,
  sourceCount,
  threeThings,
  unreadCount,
  visibleItems,
} from "./model";
import { PanelEntries, PanelLinks, PanelShell, type PanelEntry } from "./panel";
import { SectionTabs } from "./section-tabs";
import { StoryViews } from "./story-views";
import { UndoToast } from "./toast";
import { useReaderCore } from "./use-reader-core";

type Props = {
  edition: Edition;
  paperName: string;
  timeZone: string;
  /** Server render time, so relative times agree between server and client. */
  now: string;
  /** Today and /paper/[date] have the sections panel; the archive has its own edition list. */
  sectionsPanel: boolean;
};

/** One finished edition: sections panel, section tabs, and the stories in the chosen view. */
export function EditionWorkspace({ edition, paperName, timeZone, now, sectionsPanel }: Props) {
  const { view, query, closeDrawer } = useChrome();
  const [section, setSection] = useState(FRONT_PAGE);
  const sections = useMemo(() => sectionsOf(edition), [edition]);
  const initial = useMemo(() => initialStates(edition.items), [edition.items]);
  const nowDate = useMemo(() => new Date(now), [now]);
  useActiveEdition({ date: edition.date, ready: edition.status === "ready" });

  const chooseVisible = useCallback(
    (states: ItemStates) => visibleItems(sections, section, states, query),
    [sections, section, query],
  );
  const core = useReaderCore(initial, view, chooseVisible);
  const items = core.items;

  const unread = unreadCount(edition.items, core.states);
  const entries: PanelEntry[] = [
    { key: FRONT_PAGE, label: "Front page", count: unread },
    ...sections.map((s) => ({ key: s.name, label: s.name, count: unreadCount(s.items, core.states) })),
  ];
  const select = (key: string) => {
    setSection(key);
    closeDrawer();
    window.scrollTo({ top: 0 });
  };
  const heading = query.trim() ? `Search: “${query.trim()}”` : section === FRONT_PAGE ? "Front page" : section;
  const total = edition.items.length;

  return (
    <div className="flex flex-1 items-stretch">
      {sectionsPanel ? (
        <PanelShell label="Sections">
          <div className="flex w-full flex-col p-4">
            <p className="font-display text-lg leading-tight font-black">{paperName}</p>
            <p className="font-sans text-[0.7rem] tracking-[0.12em] text-muted uppercase">
              {formatDateLine(edition.date + "T12:00:00Z", timeZone)}
            </p>
            <p className="mt-1 font-sans text-xs text-muted">
              {readCount(edition.items, core.states)} of {total} read · from {sourceCount(edition)} sources
            </p>
            <Rule variant="thin" className="my-3" />
            <PanelEntries label="Sections" entries={entries} selected={section} onSelect={select} />
            <PanelLinks />
          </div>
        </PanelShell>
      ) : null}

      <div className="min-w-0 flex-1 px-4 pt-4 pb-16 sm:px-6">
        <SectionTabs
          entries={entries}
          selected={section}
          onSelect={select}
          className={sectionsPanel ? "lg:hidden" : undefined}
        />
        <header className="mt-4 mb-5">
          <p className="kicker text-muted">
            {formatDateLine(edition.date + "T12:00:00Z", timeZone)} · No. {edition.number}
            {sectionsPanel ? null : ` · ${readCount(edition.items, core.states)} of ${total} read`}
          </p>
          <h1 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
            {edition.title && section === FRONT_PAGE && !query.trim() ? edition.title : heading}
          </h1>
          {edition.editor_note && section === FRONT_PAGE && !query.trim() ? (
            <p className="mt-2 max-w-prose font-serif text-base text-muted italic">{edition.editor_note}</p>
          ) : null}
        </header>
        <StoryViews
          view={view}
          items={items}
          core={core}
          now={nowDate}
          threeThings={section === FRONT_PAGE ? threeThings(edition.layout) : []}
          emptyMessage={
            query.trim()
              ? "Nothing in this paper matches your search."
              : "You've seen everything in this section."
          }
        />
        <p className="mt-10 hidden font-sans text-xs text-muted md:block">
          Keyboard: <kbd>j</kbd>/<kbd>k</kbd> move · <kbd>Enter</kbd> expand · <kbd>o</kbd> open · <kbd>s</kbd> save ·{" "}
          <kbd>m</kbd>/<kbd>l</kbd> more/less like this · <kbd>x</kbd> skip · <kbd>Shift</kbd>+<kbd>A</kbd> mark all read
        </p>
      </div>
      <UndoToast toast={core.toast} onDismiss={core.dismissToast} />
    </div>
  );
}
