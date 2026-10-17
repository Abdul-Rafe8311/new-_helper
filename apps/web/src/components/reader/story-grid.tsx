"use client";

import type { EditionItem } from "@/lib/api";

import { spanFor, stateFor } from "./model";
import { StoryCard } from "./story-card";
import type { ReaderCore } from "./use-reader-core";

const XL_SPAN: Record<number, string> = { 4: "xl:col-span-4", 5: "xl:col-span-5", 7: "xl:col-span-7" };

/** Wide screens: 12 columns, rows of varied widths. Tablet: two columns. Phone: one. */
export function gridSpan(index: number): string {
  return `${index === 0 ? "sm:col-span-2" : ""} ${XL_SPAN[spanFor(index)]}`.trim();
}

const GRID = "grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-12 xl:auto-rows-[minmax(320px,auto)]";

export function StoryGrid({
  items,
  core,
  now,
}: {
  items: EditionItem[];
  core: Pick<ReaderCore, "states" | "actions" | "focusedId">;
  now: Date;
}) {
  return (
    <div className={`${GRID} fade-quick`}>
      {items.map((item, index) => (
        <StoryCard
          key={item.id}
          item={item}
          state={stateFor(core.states, item)}
          actions={core.actions}
          now={now}
          span={gridSpan(index)}
          lead={index === 0}
          focused={core.focusedId === item.id}
        />
      ))}
    </div>
  );
}

/** Same shape as the real grid, so nothing jumps when the stories arrive. */
export function StoryGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div aria-busy="true" role="status" aria-label="Loading stories" className={GRID}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={`min-h-[320px] animate-pulse rounded-[14px] bg-paper-2 ${gridSpan(i)}`} />
      ))}
      <span className="sr-only">Loading stories…</span>
    </div>
  );
}
