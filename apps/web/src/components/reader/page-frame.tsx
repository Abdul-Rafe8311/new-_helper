import type { ReactNode } from "react";

/** Navigation on the left (240px on desktop), the page's content to its right. */
export function PageFrame({ nav, children }: { nav: ReactNode; children: ReactNode }) {
  return (
    <div className="relative z-10 mx-auto flex w-full max-w-[1680px] flex-1 items-start gap-0 px-4 lg:px-8">
      {nav}
      <main id="main" className="min-w-0 flex-1 pb-24">
        {children}
      </main>
    </div>
  );
}
