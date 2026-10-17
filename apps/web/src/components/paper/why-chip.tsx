"use client";

import { Sparkle } from "lucide-react";
import { Popover } from "radix-ui";
import { useState } from "react";

import { cn } from "@/lib/utils";

import { explainScore } from "./score-breakdown";

type WhyChipProps = {
  reason: string;
  /** The composer's score breakdown; when present the chip opens a tooltip with the details. */
  breakdown?: Record<string, unknown> | null;
  className?: string;
};

const CHIP =
  "inline-flex max-w-full items-start gap-1 rounded-xl border border-accent/40 px-2 py-0.5 text-left font-sans text-[0.7rem] leading-4 text-accent";

/** Explains in a few words why a story is in this reader's paper, and how it scored. */
export function WhyChip({ reason, breakdown, className }: WhyChipProps) {
  const [open, setOpen] = useState(false);
  const explained = explainScore(breakdown);

  const label = (
    <>
      <Sparkle aria-hidden="true" className="mt-0.5 size-3 shrink-0" />
      <span className="sr-only">Why you&apos;re seeing this: </span>
      <span>{reason}</span>
    </>
  );
  if (!explained) return <span className={cn(CHIP, className)}>{label}</span>;

  const widest = Math.max(1, ...explained.rows.map((row) => row.points));
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className={cn(CHIP, "cursor-help outline-none hover:bg-accent/10 focus-visible:ring-[3px] focus-visible:ring-ring/50", className)}
        aria-label={`Why you're seeing this: ${reason}. Show score breakdown`}
      >
        {label}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="top"
          align="start"
          sideOffset={6}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          className="z-50 w-72 rounded-md border border-rule bg-paper p-3 font-sans text-xs text-ink shadow-lg"
        >
          <p className="flex items-baseline justify-between">
            <span className="kicker">Score breakdown</span>
            <span className="text-sm font-semibold">{explained.total}/100</span>
          </p>
          <ul className="mt-2 space-y-1.5">
            {explained.rows.map((row) => (
              <li key={row.key}>
                <div className="flex justify-between gap-2">
                  <span>{row.label}</span>
                  <span className="text-muted tabular-nums">+{row.points}</span>
                </div>
                <div className="mt-0.5 h-1 bg-paper-2">
                  <div className="h-full bg-accent" style={{ width: `${(row.points / widest) * 100}%` }} />
                </div>
              </li>
            ))}
            {explained.penalties.map((row) => (
              <li key={row.key} className="flex justify-between gap-2 text-destructive">
                <span>{row.label}</span>
                <span className="tabular-nums">-{Math.abs(row.points)}</span>
              </li>
            ))}
          </ul>
          {explained.notes.length ? (
            <p className="mt-2 border-t border-rule pt-2 text-muted">{explained.notes.join(" · ")}</p>
          ) : null}
          <Popover.Arrow className="fill-rule" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
