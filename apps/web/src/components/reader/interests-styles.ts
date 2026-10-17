import { cn } from "@/lib/utils";

export const focusRing = "outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";
export const pill = cn(
  "inline-flex min-h-9 items-center gap-1.5 rounded-full border border-rule px-3 font-sans text-sm font-semibold hover:bg-paper-2",
  focusRing,
);
