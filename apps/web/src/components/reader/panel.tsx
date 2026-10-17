"use client";

import { Archive, Bookmark } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { useChrome } from "./chrome-context";

/**
 * The 260px column left of the articles. Open by default on desktop, collapsed on tablets, and a
 * drawer on phones; the toolbar's panel button toggles it.
 */
export function PanelShell({ label, children }: { label: string; children: ReactNode }) {
  const { panelOpen, setPanelOpen } = useChrome();
  return (
    <>
      {panelOpen === true ? (
        <button
          type="button"
          aria-label="Close panel"
          onClick={() => setPanelOpen(null)}
          className="fixed inset-0 z-30 bg-ink/40 md:hidden"
        />
      ) : null}
      <aside
        aria-label={label}
        className={cn(
          "w-[260px] shrink-0 flex-col overflow-y-auto border-r border-rule bg-paper",
          "max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-40 max-md:shadow-xl",
          "md:sticky md:top-[var(--toolbar-h,49px)] md:h-[calc(100vh-var(--toolbar-h,49px))]",
          panelOpen === true ? "flex" : panelOpen === false ? "hidden" : "hidden lg:flex",
        )}
      >
        {children}
      </aside>
    </>
  );
}

export type PanelEntry = { key: string; label: string; count?: number; hint?: string };

/** Selectable rows with small count badges. */
export function PanelEntries({
  entries,
  selected,
  onSelect,
  label,
  countLabel = "unread",
}: {
  entries: PanelEntry[];
  selected: string;
  onSelect: (key: string) => void;
  label: string;
  countLabel?: string;
}) {
  return (
    <ul aria-label={label} className="space-y-0.5">
      {entries.map((entry) => {
        const active = entry.key === selected;
        return (
          <li key={entry.key}>
            <button
              type="button"
              aria-current={active ? "true" : undefined}
              onClick={() => onSelect(entry.key)}
              className={cn(
                "flex w-full items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-left font-sans text-sm outline-none",
                "focus-visible:ring-[3px] focus-visible:ring-ring/50",
                active ? "bg-paper-2 font-semibold text-ink" : "text-ink/80 hover:bg-paper-2/70",
              )}
            >
              <span className="min-w-0 truncate">{entry.label}</span>
              {entry.count ? (
                <span
                  className={cn(
                    "shrink-0 rounded-full px-1.5 text-[0.7rem] leading-5 font-semibold tabular-nums",
                    active ? "bg-accent text-accent-ink" : "bg-accent/15 text-accent",
                  )}
                >
                  {entry.count}
                  <span className="sr-only"> {countLabel}</span>
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

const LINK =
  "flex items-center gap-2 rounded-md px-2.5 py-1.5 font-sans text-sm text-ink/80 outline-none hover:bg-paper-2/70 focus-visible:ring-[3px] focus-visible:ring-ring/50";

/** "Saved" and "Archive", under a divider at the foot of the panel. */
export function PanelLinks() {
  const { closeDrawer } = useChrome();
  return (
    <nav aria-label="Library" className="mt-4 space-y-0.5 border-t border-rule pt-3">
      <Link href="/saved" className={LINK} onClick={closeDrawer}>
        <Bookmark aria-hidden="true" className="size-4 text-muted" /> Saved
      </Link>
      <Link href="/archive" className={LINK} onClick={closeDrawer}>
        <Archive aria-hidden="true" className="size-4 text-muted" /> Archive
      </Link>
    </nav>
  );
}
