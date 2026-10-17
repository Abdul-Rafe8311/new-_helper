"use client";

import { Bookmark } from "lucide-react";
import { useCallback, useMemo } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import type { SavedItem } from "@/lib/api";

import { useAccent, useActiveEdition } from "./chrome-context";
import { EditionHeader } from "./edition-header";
import { stateFor, type ItemStates } from "./model";
import { FRONT_COLOR } from "./palette";
import { PageFrame } from "./page-frame";
import { SideNav } from "./side-nav";
import { StoryGrid } from "./story-grid";
import { UndoToast } from "./toast";
import { useReaderCore } from "./use-reader-core";

/** Stories the reader saved, from every edition. Un-saving one removes it from the page. */
export function SavedWorkspace({ items, now }: { items: SavedItem[]; now: string }) {
  const nowDate = useMemo(() => new Date(now), [now]);
  useActiveEdition(null);
  useAccent(FRONT_COLOR);
  const choose = useCallback(
    (states: ItemStates) =>
      items.filter((item) => {
        const state = stateFor(states, item);
        return state.saved && !state.skipped;
      }),
    [items],
  );
  const core = useReaderCore(choose);

  return (
    <PageFrame nav={<SideNav base="/today" />}>
      <EditionHeader title="Saved" dateLine="Set aside to come back to" />
      {core.items.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="Nothing saved yet."
          body="Use the bookmark on any story to keep it here."
          action={{ href: "/today", label: "Back to today's paper" }}
        />
      ) : (
        <StoryGrid items={core.items} core={core} now={nowDate} />
      )}
      <UndoToast toast={core.toast.toast} onDismiss={core.toast.dismiss} />
    </PageFrame>
  );
}
