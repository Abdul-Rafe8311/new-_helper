import { cn } from "@/lib/utils";

type RuleProps = {
  variant?: "thin" | "thick" | "double" | "dotted";
  orientation?: "horizontal" | "vertical";
  className?: string;
};

const horizontal = {
  thin: "border-t border-rule",
  thick: "border-t-[3px] border-ink",
  double: "h-[5px] border-y border-ink",
  dotted: "border-t border-dotted border-rule",
} as const;

/** Newspaper rule: thin column rules, a thick rule under the masthead, double rules between sections. */
export function Rule({ variant = "thin", orientation = "horizontal", className }: RuleProps) {
  if (orientation === "vertical") {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn("w-px self-stretch bg-rule", className)}
      />
    );
  }
  return <hr data-variant={variant} className={cn("w-full border-0", horizontal[variant], className)} />;
}
