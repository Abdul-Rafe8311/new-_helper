"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, type CSSProperties } from "react";

import type { EditionItem, ItemState } from "@/lib/api";
import { cn } from "@/lib/utils";

import { FeedbackActions } from "./feedback-actions";
import { outletCount, relativeTime } from "./model";
import { categoryColor } from "./palette";
import { useStoryTracking } from "./tracking-provider";
import type { ItemActions } from "./use-item-actions";

export function StoryImage({
  item,
  color,
  priority = false,
  sizes,
}: {
  item: EditionItem;
  color: string;
  priority?: boolean;
  sizes: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!item.image_url || failed) {
    // A deliberate stand-in: the category colour with the outlet's initial, not a grey box.
    return (
      <div
        aria-hidden="true"
        data-testid="image-fallback"
        className="absolute inset-0 flex items-center justify-center overflow-hidden bg-[linear-gradient(135deg,color-mix(in_oklab,var(--c)_55%,#fff),color-mix(in_oklab,var(--c)_92%,#000))] font-display text-[9rem] leading-none font-black text-white/20 select-none"
        style={{ "--c": color } as CSSProperties}
      >
        {(item.source.trim()[0] ?? "N").toUpperCase()}
      </div>
    );
  }
  return (
    <Image
      src={item.image_url}
      alt=""
      fill
      unoptimized
      priority={priority}
      sizes={sizes}
      onError={() => setFailed(true)}
      className="object-cover"
    />
  );
}

type StoryCardProps = {
  item: EditionItem;
  state: ItemState;
  actions: ItemActions;
  now: Date;
  /** Grid classes that give this card its width. */
  span: string;
  /** Only the lead story's picture is loaded eagerly. */
  lead?: boolean;
  focused?: boolean;
  onSkipped?: () => void;
};

/**
 * One story: photo above, a saturated colour panel below. The headline is the only link (stretched
 * over the card); the save and feedback buttons sit beside it, so no control is nested in another.
 */
export function StoryCard({ item, state, actions, now, span, lead = false, focused = false, onSkipped }: StoryCardProps) {
  const color = categoryColor(item.section);
  const track = useStoryTracking(item.id);
  const outlets = outletCount(item);
  const age = relativeTime(item.published_at, now);

  return (
    <article
      ref={track as never}
      id={`story-${item.id}`}
      data-story={item.id}
      data-focused={focused}
      className={cn("story-card group relative min-w-0", span)}
      style={{ "--c": color, "--cat": color, "--panel": `color-mix(in oklab, ${color} 84%, #000)` } as CSSProperties}
    >
      <div className="story-card__surface relative flex h-full min-h-[320px] flex-col overflow-hidden rounded-[14px] bg-[var(--panel)] text-white shadow-sm">
        <div className="relative min-h-44 flex-1 bg-[var(--panel)]">
          <StoryImage
            item={item}
            color={color}
            priority={lead}
            sizes={lead ? "(min-width: 1280px) 700px, (min-width: 640px) 90vw, 100vw" : "(min-width: 1280px) 420px, (min-width: 640px) 50vw, 100vw"}
          />
          <div aria-hidden="true" className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-b from-transparent to-[var(--panel)]" />
        </div>
        <div className="relative px-4 pt-1 pb-4">
          <p className="flex flex-wrap items-center gap-x-2 font-sans text-[12px] font-medium tracking-wide text-white/80">
            {!state.read ? (
              <span role="img" aria-label="Unread" className="size-1.5 rounded-full bg-white" />
            ) : null}
            <span className="font-semibold text-white">{item.source}</span>
            {age ? <time dateTime={item.published_at ?? undefined}>{age}</time> : null}
            {outlets ? <span>{outlets} outlets</span> : null}
          </p>
          <h2 className={cn("mt-1.5 font-sans font-extrabold tracking-tight text-balance", lead ? "text-2xl leading-[1.15] xl:text-[26px]" : "text-[19px] leading-[1.2] xl:text-[21px]")}>
            <Link
              href={`/story/${item.id}`}
              data-story-link
              className="outline-none after:absolute after:inset-0 after:content-['']"
            >
              {item.headline}
            </Link>
          </h2>
          {item.summary ? (
            <p className="mt-2 line-clamp-3 font-sans text-[14px] leading-snug text-white/85 sm:text-[15px]">{item.summary}</p>
          ) : null}
        </div>
        <div className="story-card__actions absolute top-3 right-3 z-10">
          <FeedbackActions item={item} state={state} actions={actions} variant="icons" onSkipped={onSkipped} />
        </div>
      </div>
    </article>
  );
}
