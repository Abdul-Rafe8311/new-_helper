import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { formatDateLine } from "./format";
import { Rule } from "./rule";

type MastheadProps = {
  paperName: string;
  date: Date | string;
  editionNumber?: number;
  /** Slot for the weather (filled in a later task) */
  weather?: ReactNode;
  tagline?: string;
  timeZone?: string;
  size?: "lg" | "md";
  className?: string;
};

/** The paper's nameplate: dateline, the paper's name in display type, and a double rule. */
export function Masthead({
  paperName,
  date,
  editionNumber,
  weather,
  tagline,
  timeZone,
  size = "lg",
  className,
}: MastheadProps) {
  return (
    <header className={cn("text-center", className)}>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 pb-2 font-sans text-[0.7rem] uppercase tracking-[0.12em] text-muted">
        <span>{editionNumber ? `No. ${editionNumber}` : "First edition"}</span>
        <span className="order-last w-full sm:order-none sm:w-auto">{formatDateLine(date, timeZone)}</span>
        <span data-slot="weather">{weather ?? " "}</span>
      </div>
      <Rule variant="thin" />
      <h1
        className={cn(
          "py-3 font-display font-black leading-none tracking-tight text-ink",
          size === "lg" ? "text-5xl sm:text-7xl" : "text-3xl sm:text-5xl",
        )}
      >
        {paperName}
      </h1>
      {tagline ? <p className="pb-2 font-serif text-sm italic text-muted">{tagline}</p> : null}
      <Rule variant="double" />
    </header>
  );
}
