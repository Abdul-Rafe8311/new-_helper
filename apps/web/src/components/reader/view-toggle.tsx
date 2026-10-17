"use client";

import { LayoutGrid, LayoutList, Newspaper, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

import { useChrome } from "./chrome-context";
import type { ViewMode } from "./model";

const OPTIONS: { mode: ViewMode; label: string; icon: LucideIcon }[] = [
  { mode: "list", label: "List", icon: LayoutList },
  { mode: "cards", label: "Cards", icon: LayoutGrid },
  { mode: "newspaper", label: "Newspaper", icon: Newspaper },
];

/** List / Cards / Newspaper, as a segmented control. */
export function ViewToggle() {
  const { view, setView } = useChrome();
  return (
    <div role="group" aria-label="View" className="inline-flex rounded-md border border-rule p-0.5">
      {OPTIONS.map(({ mode, label, icon: Icon }) => (
        <button
          key={mode}
          type="button"
          aria-pressed={view === mode}
          aria-label={`${label} view`}
          title={`${label} view`}
          onClick={() => setView(mode)}
          className={cn(
            "inline-flex h-7 items-center gap-1.5 rounded-sm px-2 font-sans text-xs outline-none transition-colors",
            "focus-visible:ring-[3px] focus-visible:ring-ring/50",
            view === mode ? "bg-ink text-paper" : "text-muted hover:text-ink",
          )}
        >
          <Icon aria-hidden="true" className="size-3.5" />
          <span className="hidden xl:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}
