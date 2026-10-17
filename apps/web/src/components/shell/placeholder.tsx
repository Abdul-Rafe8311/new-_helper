import type { ReactNode } from "react";

import { SectionHeader } from "@/components/paper";

/** Stand-in body for pages that later tasks fill in. */
export function Placeholder({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mx-auto max-w-2xl py-10">
      <SectionHeader title={title} />
      <div className="font-serif text-lg leading-relaxed text-muted">{children}</div>
    </section>
  );
}
