"use client";

import { Bookmark, ExternalLink, ThumbsDown, ThumbsUp, X } from "lucide-react";
import Image from "next/image";
import { useState, type ReactNode } from "react";

import { WhyChip } from "@/components/paper";
import { originalHref, type EditionItem, type ItemState } from "@/lib/api";
import { cn } from "@/lib/utils";

import { hostOf } from "./model";
import type { ReaderActions } from "./use-reader-core";
import { useStoryTracking } from "./tracking-provider";

/** Wraps one story: its DOM id (for keyboard focus), impression tracking and the focus ring. */
export function StoryShell({
  item,
  state,
  focused,
  as: Tag = "article",
  className,
  children,
}: {
  item: EditionItem;
  state: ItemState;
  focused: boolean;
  as?: "article" | "div";
  className?: string;
  children: ReactNode;
}) {
  const track = useStoryTracking(item.id);
  return (
    <Tag
      ref={track as never}
      id={`story-${item.id}`}
      data-story={item.id}
      data-read={state.read}
      data-focused={focused}
      tabIndex={-1}
      className={cn(
        "scroll-mt-28 outline-none data-[focused=true]:ring-2 data-[focused=true]:ring-accent/60 data-[focused=true]:ring-offset-4 data-[focused=true]:ring-offset-paper",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function UnreadDot({ unread }: { unread: boolean }) {
  return unread ? (
    <span
      role="img"
      aria-label="Unread"
      className="inline-block size-2 shrink-0 rounded-full bg-accent"
    />
  ) : null;
}

/** The source's favicon, or its first letter if that cannot be loaded. */
export function Favicon({ url, source }: { url: string; source: string }) {
  const host = hostOf(url);
  const [failed, setFailed] = useState(false);
  const letter = (source.trim()[0] ?? "?").toUpperCase();
  if (!host || failed) {
    return (
      <span
        aria-hidden="true"
        className="inline-flex size-5 shrink-0 items-center justify-center rounded-sm bg-paper-2 font-sans text-[0.65rem] font-semibold text-muted"
      >
        {letter}
      </span>
    );
  }
  return (
    <Image
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=32`}
      alt=""
      width={20}
      height={20}
      unoptimized
      onError={() => setFailed(true)}
      className="size-5 shrink-0 rounded-sm"
    />
  );
}

/** A story's picture, or a halftone stand-in. */
export function StoryImage({
  item,
  priority = false,
  className,
  sizes,
}: {
  item: EditionItem;
  priority?: boolean;
  className?: string;
  sizes: string;
}) {
  return (
    <div className={cn("relative overflow-hidden bg-paper-2", className)}>
      {item.image_url ? (
        <Image
          src={item.image_url}
          alt=""
          fill
          unoptimized
          priority={priority}
          sizes={sizes}
          className="object-cover grayscale-[15%]"
        />
      ) : (
        <div aria-hidden="true" className="halftone absolute inset-0" />
      )}
    </div>
  );
}

const ACTION =
  "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 font-sans text-xs font-medium outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50";

function ToggleAction({
  label,
  hint,
  pressed,
  onClick,
  icon,
}: {
  label: string;
  hint: string;
  pressed: boolean;
  onClick: () => void;
  icon: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      title={`${label} (${hint})`}
      onClick={onClick}
      className={cn(
        ACTION,
        pressed ? "border-accent bg-accent/10 text-accent" : "border-rule text-ink hover:bg-paper-2",
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

/** Read original, Save, More / Less like this and Skip. */
export function StoryActions({
  item,
  state,
  actions,
}: {
  item: EditionItem;
  state: ItemState;
  actions: ReaderActions;
}) {
  return (
    <div role="group" aria-label="Story actions" className="flex flex-wrap gap-2">
      <a
        href={originalHref(item.id)}
        target="_blank"
        rel="noopener noreferrer"
        title="Read original (o)"
        onClick={() => actions.opened(item.id)}
        className={cn(ACTION, "border-accent bg-accent text-accent-ink hover:bg-accent/90")}
      >
        <ExternalLink aria-hidden="true" className="size-3.5" />
        Read original
      </a>
      <ToggleAction
        label={state.saved ? "Saved" : "Save"}
        hint="s"
        pressed={state.saved}
        onClick={() => actions.toggleSave(item.id)}
        icon={<Bookmark aria-hidden="true" className={cn("size-3.5", state.saved && "fill-current")} />}
      />
      <ToggleAction
        label="More like this"
        hint="m"
        pressed={state.reaction === "more"}
        onClick={() => actions.react(item.id, "more")}
        icon={<ThumbsUp aria-hidden="true" className="size-3.5" />}
      />
      <ToggleAction
        label="Less like this"
        hint="l"
        pressed={state.reaction === "less"}
        onClick={() => actions.react(item.id, "less")}
        icon={<ThumbsDown aria-hidden="true" className="size-3.5" />}
      />
      <button
        type="button"
        title="Skip (x)"
        onClick={() => actions.skip(item.id)}
        className={cn(ACTION, "border-rule text-muted hover:bg-paper-2 hover:text-ink")}
      >
        <X aria-hidden="true" className="size-3.5" />
        Skip
      </button>
    </div>
  );
}

/** What a story shows once expanded: full summary, key facts, why, and the actions. */
export function StoryDetail({
  item,
  state,
  actions,
  id,
}: {
  item: EditionItem;
  state: ItemState;
  actions: ReaderActions;
  id: string;
}) {
  return (
    <div id={id} className="mt-3 space-y-3 border-t border-rule pt-3">
      {item.summary ? <p className="font-serif text-base leading-relaxed text-ink">{item.summary}</p> : null}
      {item.key_facts.length > 0 ? (
        <ul aria-label="Key facts" className="flex flex-wrap gap-1.5">
          {item.key_facts.map((fact) => (
            <li key={fact} className="rounded-full bg-paper-2 px-2.5 py-1 font-sans text-xs text-ink">
              {fact}
            </li>
          ))}
        </ul>
      ) : null}
      {item.why_text ? <WhyChip reason={item.why_text} breakdown={item.score_breakdown} /> : null}
      <StoryActions item={item} state={state} actions={actions} />
    </div>
  );
}
