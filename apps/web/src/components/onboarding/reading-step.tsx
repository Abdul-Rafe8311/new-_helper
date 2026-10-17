"use client";

import { useId, type ReactNode } from "react";

import { cn } from "@/lib/utils";

import type { Depth, ReadingMinutes } from "./machine";
import { StepHeading } from "./step-heading";
import type { StepProps } from "./steps-props";

const MINUTES: { value: ReadingMinutes; label: string; note: string }[] = [
  { value: 5, label: "5 min", note: "A quick scan" },
  { value: 10, label: "10 min", note: "Over coffee" },
  { value: 20, label: "20 min", note: "A proper read" },
];

const DEPTHS: { value: Depth; label: string; note: string }[] = [
  { value: "brief", label: "Headlines", note: "Just the facts, fast" },
  { value: "balanced", label: "Balanced", note: "A mix of short and long" },
  { value: "deep", label: "Deep dives", note: "Fewer stories, more depth" },
];

export function ReadingStep({ draft, dispatch }: StepProps) {
  const surpriseId = useId();
  return (
    <section>
      <StepHeading step={5} title="How do you read?" lede="So your paper fits the time you actually have." />

      <div className="space-y-8">
        <Choice
          legend="How long do you have each morning?"
          options={MINUTES}
          value={draft.readingMinutes}
          onChange={(minutes) => dispatch({ type: "set_reading", minutes })}
        />
        <Choice
          legend="How deep do you like to go?"
          options={DEPTHS}
          value={draft.depth}
          onChange={(depth) => dispatch({ type: "set_depth", depth })}
        />

        <div className="flex items-start gap-4 border-y border-rule py-4">
          <button
            id={surpriseId}
            type="button"
            role="switch"
            aria-checked={draft.surpriseMe}
            aria-labelledby={`${surpriseId}-label`}
            aria-describedby={`${surpriseId}-note`}
            onClick={() => dispatch({ type: "set_surprise", on: !draft.surpriseMe })}
            className={cn(
              "relative mt-0.5 h-7 w-12 shrink-0 rounded-full border border-ink outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50",
              draft.surpriseMe ? "bg-accent" : "bg-paper-2",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "absolute top-0.5 left-0.5 size-5.5 rounded-full bg-paper shadow transition-transform",
                draft.surpriseMe ? "translate-x-5" : "translate-x-0",
              )}
            />
          </button>
          <div>
            <label id={`${surpriseId}-label`} htmlFor={surpriseId} className="font-sans text-sm font-medium">
              Surprise me with things outside my bubble
            </label>
            <p id={`${surpriseId}-note`} className="font-serif text-base text-muted">
              A few stories from beyond your usual topics, so your paper never gets stale.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function Choice<T extends string | number>({
  legend,
  options,
  value,
  onChange,
}: {
  legend: ReactNode;
  options: { value: T; label: string; note: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-3 font-sans text-sm font-medium">{legend}</legend>
      <div role="radiogroup" aria-label={typeof legend === "string" ? legend : undefined} className="grid gap-3 sm:grid-cols-3">
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(option.value)}
              className={cn(
                "flex min-h-16 flex-col items-start rounded-sm border px-4 py-3 text-left outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50",
                selected ? "border-ink bg-ink text-paper" : "border-ink/40 hover:border-ink hover:bg-paper-2",
              )}
            >
              <span className="font-display text-xl font-black">{option.label}</span>
              <span className={cn("font-sans text-xs", selected ? "text-paper/80" : "text-muted")}>{option.note}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
