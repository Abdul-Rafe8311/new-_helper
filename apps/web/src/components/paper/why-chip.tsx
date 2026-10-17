import { Sparkle } from "lucide-react";

import { cn } from "@/lib/utils";

/** Explains in a few words why a story is in this reader's paper. */
export function WhyChip({ reason, className }: { reason: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-full border border-accent/40 px-2 py-0.5 font-sans text-[0.7rem] leading-4 text-accent",
        className,
      )}
    >
      <Sparkle aria-hidden="true" className="size-3 shrink-0" />
      <span className="sr-only">Why you&apos;re seeing this: </span>
      <span className="truncate">{reason}</span>
    </span>
  );
}
