"use client";

import { SectionHeader } from "@/components/paper";
import type { SourceCatalogue } from "@/lib/api";
import { cn } from "@/lib/utils";

import { pill } from "./interests-styles";

type Props = {
  catalogue: SourceCatalogue;
  /** Names the reader has switched off. */
  off: ReadonlySet<string>;
  onToggle: (name: string, on: boolean) => void;
};

/** The outlets that feed the paper, grouped by section; each is a switch the reader can turn off. */
export function SourceToggles({ catalogue, off, onToggle }: Props) {
  return (
    <section aria-labelledby="sources-h" className="mb-10">
      <SectionHeader title="Sources" description="Switch off any outlet you would rather not read" />
      <h3 id="sources-h" className="sr-only">
        Sources that feed your paper
      </h3>
      <div className="flex flex-col gap-5">
        {catalogue.sections.map((section) => {
          const sources = catalogue.sources.filter((s) => s.section === section);
          if (sources.length === 0) return null;
          return (
            <div key={section} role="group" aria-label={section}>
              <h4 className="font-sans text-sm font-bold tracking-wide text-muted uppercase">{section}</h4>
              <ul className="mt-2 flex flex-wrap gap-2">
                {sources.map((s) => {
                  const on = !off.has(s.name);
                  return (
                    <li key={s.name}>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={on}
                        onClick={() => onToggle(s.name, !on)}
                        className={cn(pill, on ? "border-accent bg-accent/10" : "text-muted line-through")}
                      >
                        {s.name}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
