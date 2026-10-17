"use client";

import { cn } from "@/lib/utils";

import type { PanelEntry } from "./panel";

/** Horizontally scrolling section tabs, sticky under the toolbar. Phones, and the archive. */
export function SectionTabs({
  entries,
  selected,
  onSelect,
  className,
}: {
  entries: PanelEntry[];
  selected: string;
  onSelect: (key: string) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "sticky top-[var(--toolbar-h,49px)] z-10 -mx-4 border-b border-rule bg-paper/95 px-4 backdrop-blur sm:-mx-6 sm:px-6",
        className,
      )}
    >
      <div role="tablist" aria-label="Sections" className="flex gap-1 overflow-x-auto py-1.5 [scrollbar-width:none]">
        {entries.map((entry) => {
          const active = entry.key === selected;
          return (
            <button
              key={entry.key}
              role="tab"
              type="button"
              aria-selected={active}
              onClick={() => onSelect(entry.key)}
              className={cn(
                "kicker shrink-0 border-b-2 px-2.5 py-2 whitespace-nowrap outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                active ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink",
              )}
            >
              {entry.label}
              {entry.count ? <span className="ml-1.5 text-accent tabular-nums">{entry.count}</span> : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
