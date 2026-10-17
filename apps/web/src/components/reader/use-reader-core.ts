"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { originalHref, type EditionItem } from "@/lib/api";

import { useChrome } from "./chrome-context";
import { stateFor, type ItemStates } from "./model";
import { useItemActions, type ItemActions, type ToastApi } from "./use-item-actions";

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName);
}

/** The link that opens a story, which keyboard focus lands on. */
export function storyLink(id: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(`#story-${CSS.escape(id)} [data-story-link]`);
}

/**
 * The feed's behaviour: which stories are shown, keyboard focus, the actions and their toast.
 *
 *   j / k  next / previous story   o  open original   s  save
 *   m / l  more / less like this   x  skip            Shift+A  mark all shown as read
 * (Enter on a focused story follows its link, like any link.)
 */
export function useReaderCore(select: (states: ItemStates) => EditionItem[]) {
  const { states } = useChrome();
  const { actions, toast } = useItemActions("feed");
  const items = useMemo(() => select(states), [select, states]);
  const [focusedId, setFocusedId] = useState<string | null>(null);

  const live = useRef({ items, focusedId });
  useEffect(() => {
    live.current = { items, focusedId };
  });

  const focusStory = useCallback((id: string) => {
    setFocusedId(id);
    const link = storyLink(id);
    if (!link) return;
    link.focus({ preventScroll: true });
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    link.scrollIntoView({ block: "nearest", behavior: calm ? "auto" : "smooth" });
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      const { items: shown, focusedId: focus } = live.current;
      const index = shown.findIndex((item) => item.id === focus);
      const current = index >= 0 ? shown[index] : null;
      const move = (to: number) => {
        const next = shown[Math.min(shown.length - 1, Math.max(0, to))];
        if (next) focusStory(next.id);
      };

      if (event.key === "A" && event.shiftKey) {
        event.preventDefault();
        actions.markRead(shown, "mark_all");
        toast.show(`Marked ${shown.length} ${shown.length === 1 ? "story" : "stories"} as read`);
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
        case "o":
        case "s":
        case "m":
        case "l":
        case "x": {
          if (!current) return;
          event.preventDefault();
          if (event.key === "o") {
            window.open(originalHref(current.id), "_blank", "noopener");
            actions.opened(current);
          } else if (event.key === "s") actions.toggleSave(current);
          else if (event.key === "m") actions.react(current, "more");
          else if (event.key === "l") actions.react(current, "less");
          else {
            const next = shown[index + 1] ?? shown[index - 1];
            actions.skip(current);
            if (next) focusStory(next.id);
          }
          break;
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actions, focusStory, toast]);

  return { items, states, focusedId, setFocusedId, actions, toast };
}

export type ReaderCore = ReturnType<typeof useReaderCore>;
export type { ItemActions, ToastApi };
export { stateFor };
