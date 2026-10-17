import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type ChipProps = Omit<ComponentProps<"button">, "type"> & {
  selected?: boolean;
  size?: "lg" | "md";
};

/** A tappable choice. `aria-pressed` carries the state for assistive tech and tests. */
export function Chip({ selected = false, size = "md", className, children, ...props }: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "inline-flex items-center justify-center rounded-sm border font-sans transition-colors outline-none",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        size === "lg" ? "min-h-11 px-4 text-[0.95rem]" : "min-h-9 px-3 text-sm",
        selected
          ? "border-ink bg-ink text-paper"
          : "border-ink/40 bg-transparent text-ink hover:border-ink hover:bg-paper-2",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/** A removable chip for the parsed "We heard" list. */
export function RemovableChip({
  label,
  onRemove,
  tone = "heard",
}: {
  label: string;
  onRemove: () => void;
  tone?: "heard" | "not";
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-9 items-center gap-1 rounded-sm border py-1 pr-1 pl-3 font-sans text-sm",
        tone === "heard" ? "border-ink bg-paper-2 text-ink" : "border-destructive/60 text-destructive",
      )}
    >
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${label}`}
        className="inline-flex size-7 items-center justify-center rounded-sm text-lg leading-none outline-none hover:bg-ink/10 focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <span aria-hidden="true">×</span>
      </button>
    </span>
  );
}
