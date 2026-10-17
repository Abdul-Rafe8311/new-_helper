"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { EditionItem } from "@/lib/api";
import { tracker } from "@/lib/tracking-client";
import type { EventType } from "@/lib/tracking";

import { useChrome } from "./chrome-context";
import { stateFor, type Reaction, type StatePatch } from "./model";

export type ItemActions = {
  /** The story is read: seen on its own page, or its original was opened. */
  markRead: (items: readonly EditionItem[], via: string) => void;
  /** The original was opened by a link that logs the open itself. */
  opened: (item: EditionItem) => void;
  toggleSave: (item: EditionItem) => void;
  /** Hides the story; `onUndo` receives a function that puts it back. */
  skip: (item: EditionItem, onSkipped?: (undo: () => void) => void) => void;
  react: (item: EditionItem, reaction: Reaction) => void;
};

const REACTION_EVENT: Record<Reaction, EventType> = { more: "more_like", less: "less_like" };

/**
 * What a reader can do to a story. Each action updates what every page shows (through the shared
 * store) and logs an event (value 1 sets it, 0 retracts it) that goes out soon after.
 */
export function useItemActions(view: string): { actions: ItemActions; toast: ToastApi } {
  const { states, patchStates } = useChrome();
  const live = useRef(states);
  useEffect(() => {
    live.current = states;
  });
  const toast = useToastState();

  const track = useCallback(
    (type: EventType, id: string, value?: number, meta: Record<string, string> = {}) =>
      tracker.track({ type, edition_item_id: id, value, meta: { view, ...meta } }, { urgent: true }),
    [view],
  );

  const actions = useMemo<ItemActions>(() => {
    const patch = (item: EditionItem, change: StatePatch["patch"]): StatePatch => ({
      id: item.id,
      base: item.state,
      patch: change,
    });
    return {
      markRead(items, via) {
        const unread = items.filter((item) => !stateFor(live.current, item).read);
        if (unread.length === 0) return;
        patchStates(unread.map((item) => patch(item, { read: true })));
        for (const item of unread) track("mark_read", item.id, undefined, { via });
      },
      opened(item) {
        // /r/{id} logs the open itself; this only updates what the page shows.
        patchStates([patch(item, { read: true })]);
      },
      toggleSave(item) {
        const on = !stateFor(live.current, item).saved;
        patchStates([patch(item, { saved: on })]);
        track("save", item.id, on ? 1 : 0);
        toast.show(on ? "Saved for later" : "Removed from saved");
      },
      skip(item, onSkipped) {
        if (stateFor(live.current, item).skipped) return;
        patchStates([patch(item, { skipped: true })]);
        track("skip", item.id, 1);
        const undo = () => {
          patchStates([patch(item, { skipped: false })]);
          track("skip", item.id, 0);
        };
        toast.show("Story skipped", undo);
        onSkipped?.(undo);
      },
      react(item, reaction) {
        const current = stateFor(live.current, item).reaction;
        if (current === reaction) {
          patchStates([patch(item, { reaction: null })]);
          track(REACTION_EVENT[reaction], item.id, 0);
          return;
        }
        if (current) track(REACTION_EVENT[current], item.id, 0);
        patchStates([patch(item, { reaction })]);
        track(REACTION_EVENT[reaction], item.id, 1);
        toast.show(reaction === "more" ? "You'll see more like this" : "You'll see less like this");
      },
    };
  }, [patchStates, toast, track]);

  return { actions, toast };
}

export type Toast = { id: number; message: string; undo?: () => void };
export type ToastApi = {
  toast: Toast | null;
  show: (message: string, undo?: () => void) => void;
  dismiss: () => void;
};



function useToastState(): ToastApi {
  const [toast, setToast] = useState<Toast | null>(null);
  const counter = useRef(0);
  const show = useCallback((message: string, undo?: () => void) => {
    counter.current += 1;
    setToast({ id: counter.current, message, undo });
  }, []);
  const dismiss = useCallback(() => setToast(null), []);
  return useMemo(() => ({ toast, show, dismiss }), [toast, show, dismiss]);
}
