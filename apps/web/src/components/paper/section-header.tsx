import { cn } from "@/lib/utils";

import { Rule } from "./rule";

type SectionHeaderProps = {
  title: string;
  /** One line under the label, e.g. the editor's framing for the section */
  description?: string;
  className?: string;
};

/** Small-caps section label over a thick rule, like "WORLD" above a column. */
export function SectionHeader({ title, description, className }: SectionHeaderProps) {
  return (
    <header className={cn("mb-4", className)}>
      <Rule variant="thick" />
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 pt-1.5">
        <h2 className="kicker text-ink">{title}</h2>
        {description ? <p className="font-serif text-sm italic text-muted">{description}</p> : null}
      </div>
    </header>
  );
}
