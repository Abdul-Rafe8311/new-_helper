"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { originalHref, type EditionItem } from "@/lib/api";
import { reduceStates, stateOf, type ItemStates, type Reaction } from "./model";
import { tracker } from "@/lib/tracking-client";
import type { EventType } from "@/lib/tracking";

export type Toast = { id: number; message: string; undo?: () => void };

export type ReaderActions = {
  open: (id: string) => void;
  /** The reader followed the "Read original" link themselves. */
  opened: (id: string) => void;
  toggleSave: (id: string) => void;
  skip: (id: string) => void;
  react: (id: string, reaction: Reaction) => void;
  markRead: (ids: readonly string[]) => void;
};

const REACTION_EVENT: Record<Reaction, EventType> = { more: "more_like", less: "less_like" };

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/**
 * Everything the article pane does: per-story state, expand/focus, the actions (each of which
 * logs an event), the undo toast and the keyboard shortcuts.
 *
 *   j / k  next / previous      o  open original     s  save
 *   m / l  more / less like     x  skip              Shift+A  mark all read
 *   Enter  expand / collapse (on the focused story)  Esc  collapse
 */
export function useReaderCore(
  initial: ItemStates,
  view: string,
  /** Which stories are on screen, given the current states (skipped ones drop out). */
  select: (states: ItemStates) => EditionItem[],
) {
  const [states, dispatch] = useReducer(reduceStates, initial);
  const visible = useMemo(() => select(states), [select, states]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const toastId = useRef(0);

  // Handlers always see the latest state without being re-created on every change.
  const live = useRef({ states, visible, focusedId, expandedId });
  useEffect(() => {
    live.current = { states, visible, focusedId, expandedId };
  });

  const track = useCallback(
    (type: EventType, id: string, value?: number, meta: Record<string, string> = {}) =>
      tracker.track({ type, edition_item_id: id, value, meta: { view, ...meta } }, { urgent: true }),
    [view],
  );

  const markRead = useCallback(
    (ids: readonly string[], via = "mark_all") => {
      const unread = ids.filter((id) => !stateOf(live.current.states, id).read);
      if (unread.length === 0) return;
      dispatch({ type: "read", ids: unread });
      for (const id of unread) track("mark_read", id, undefined, { via });
    },
    [track],
  );

  const showToast = useCallback((message: string, undo?: () => void) => {
    toastId.current += 1;
    setToast({ id: toastId.current, message, undo });
  }, []);

  const actions = useMemo<ReaderActions>(() => {
    const opened = (id: string) => {
      // The redirect endpoint logs the open itself; this only updates what the page shows.
      dispatch({ type: "read", ids: [id] });
    };
    const toggleSave = (id: string) => {
      const on = !stateOf(live.current.states, id).saved;
      dispatch({ type: "save", id, on });
      track("save", id, on ? 1 : 0);
      showToast(on ? "Saved for later" : "Removed from saved");
    };
    const skip = (id: string) => {
      if (stateOf(live.current.states, id).skipped) return;
      const { visible: shown, focusedId: focus } = live.current;
      dispatch({ type: "skip", id, on: true });
      track("skip", id, 1);
      setExpandedId((current) => (current === id ? null : current));
      if (focus === id) {
        const index = shown.findIndex((item) => item.id === id);
        setFocusedId((shown[index + 1] ?? shown[index - 1])?.id ?? null);
      }
      showToast("Story skipped", () => {
        dispatch({ type: "skip", id, on: false });
        track("skip", id, 0);
      });
    };
    const react = (id: string, reaction: Reaction) => {
      const current = stateOf(live.current.states, id).reaction;
      if (current === reaction) {
        dispatch({ type: "react", id, reaction: null });
        track(REACTION_EVENT[reaction], id, 0);
        return;
      }
      if (current) track(REACTION_EVENT[current], id, 0);
      dispatch({ type: "react", id, reaction });
      track(REACTION_EVENT[reaction], id, 1);
      showToast(reaction === "more" ? "You'll see more like this" : "You'll see less like this");
    };
    return {
      open: (id) => {
        window.open(originalHref(id), "_blank", "noopener");
        opened(id);
      },
      opened,
      toggleSave,
      skip,
      react,
      markRead: (ids) => markRead(ids),
    };
  }, [markRead, showToast, track]);

  const toggleExpanded = useCallback(
    (id: string) => {
      setFocusedId(id);
      setExpandedId((current) => (current === id ? null : id));
      if (live.current.expandedId !== id) markRead([id], "expand");
    },
    [markRead],
  );

  // Keep keyboard focus on the focused story, scrolling it into view.
  useEffect(() => {
    if (!focusedId) return;
    const element = document.getElementById(`story-${focusedId}`);
    if (!element) return;
    if (document.activeElement !== element && !element.contains(document.activeElement)) element.focus({ preventScroll: true });
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({ block: "nearest", behavior: calm ? "auto" : "smooth" });
  }, [focusedId]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      const { visible: shown, focusedId: focus } = live.current;
      const index = shown.findIndex((item) => item.id === focus);
      const move = (to: number) => {
        const next = shown[Math.min(shown.length - 1, Math.max(0, to))];
        if (next) setFocusedId(next.id);
      };
      const current = focus && index >= 0 ? focus : null;

      if (event.key === "A" && event.shiftKey) {
        event.preventDefault();
        markRead(shown.map((item) => item.id));
        showToast(`Marked ${shown.length} ${shown.length === 1 ? "story" : "stories"} as read`);
        return;
      }
      if (event.shiftKey) return;
      switch (event.key) {
        case "j":
          event.preventDefault();
          move(index + 1);
          break;
        case "k":
          event.preventDefault();
          move(index < 0 ? 0 : index - 1);
          break;
        case "Escape":
          setExpandedId(null);
          break;
        case "Enter": {
          // Only when the story itself has focus: buttons and links inside it keep their own Enter.
          const story = event.target instanceof HTMLElement ? event.target.closest("[data-story]") : null;
          if (story && event.target === story) {
            event.preventDefault();
            toggleExpanded(story.getAttribute("data-story") ?? "");
          }
          break;
        }
        case "o":
        case "s":
        case "m":
        case "l":
        case "x": {
          if (!current) return;
          event.preventDefault();
          if (event.key === "o") actions.open(current);
          else if (event.key === "s") actions.toggleSave(current);
          else if (event.key === "m") actions.react(current, "more");
          else if (event.key === "l") actions.react(current, "less");
          else actions.skip(current);
          break;
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actions, markRead, showToast, toggleExpanded]);

  return {
    states,
    items: visible,
    expandedId,
    focusedId,
    setFocusedId,
    toggleExpanded,
    actions,
    toast,
    dismissToast: useCallback(() => setToast(null), []),
  };
}

export type ReaderCore = ReturnType<typeof useReaderCore>;
