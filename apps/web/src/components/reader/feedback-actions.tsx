"use client";

import { Bookmark, ThumbsDown, ThumbsUp, X } from "lucide-react";

import type { EditionItem, ItemState } from "@/lib/api";
import { cn } from "@/lib/utils";

import type { ItemActions } from "./use-item-actions";

type Props = {
  item: EditionItem;
  state: ItemState;
  actions: ItemActions;
  /** "icons" for the corner of a card, "labelled" on the story page. */
  variant: "icons" | "labelled";
  onSkipped?: () => void;
  className?: string;
};

const ICON =
  "inline-flex size-9 items-center justify-center rounded-full bg-black/45 text-white outline-none backdrop-blur-sm transition-colors [@media(pointer:coarse)]:size-11 hover:bg-black/65 focus-visible:ring-[3px] focus-visible:ring-white aria-pressed:bg-white aria-pressed:text-black";
const LABELLED =
  "press inline-flex h-10 items-center gap-2 rounded-full border border-rule bg-surface px-4 font-sans text-sm font-semibold text-ink outline-none transition-colors hover:bg-paper-2 focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-pressed:border-cat aria-pressed:bg-cat/10 aria-pressed:text-cat";

/** Save, More like this, Less like this and Skip: separate buttons, never inside a story link. */
export function FeedbackActions({ item, state, actions, variant, onSkipped, className }: Props) {
  const labelled = variant === "labelled";
  const cls = labelled ? LABELLED : ICON;
  const text = (label: string) => (labelled ? <span>{label}</span> : <span className="sr-only">{label}</span>);
  return (
    <div role="group" aria-label="Story actions" className={cn("flex items-center gap-1.5", labelled && "flex-wrap gap-2", className)}>
      <button type="button" className={cls} aria-pressed={state.saved} title="Save (s)" onClick={() => actions.toggleSave(item)}>
        <Bookmark aria-hidden="true" className={cn("size-4", state.saved && "fill-current")} />
        {text(state.saved ? "Saved" : "Save")}
      </button>
      <button type="button" className={cls} aria-pressed={state.reaction === "more"} title="More like this (m)" onClick={() => actions.react(item, "more")}>
        <ThumbsUp aria-hidden="true" className="size-4" />
        {text("More like this")}
      </button>
      <button type="button" className={cls} aria-pressed={state.reaction === "less"} title="Less like this (l)" onClick={() => actions.react(item, "less")}>
        <ThumbsDown aria-hidden="true" className="size-4" />
        {text("Less like this")}
      </button>
      <button
        type="button"
        className={cls}
        title="Skip (x)"
        onClick={() => {
          actions.skip(item);
          onSkipped?.();
        }}
      >
        <X aria-hidden="true" className="size-4" />
        {text("Skip")}
      </button>
    </div>
  );
}
