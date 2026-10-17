import { PageFrame } from "./page-frame";
import { StoryGridSkeleton } from "./story-grid";

/** Page-shaped placeholder shown while an edition loads: header, topic pills, then the grid. */
export function ReaderSkeleton() {
  return (
    <PageFrame nav={<div className="hidden w-60 shrink-0 lg:block" aria-hidden="true" />}>
      <div aria-hidden="true" className="pt-4 pb-6">
        <div className="h-4 w-48 animate-pulse rounded bg-paper-2" />
        <div className="mt-3 h-[clamp(2.25rem,6.2vw,4.5rem)] w-72 max-w-full animate-pulse rounded bg-paper-2" />
        <div className="mt-5 flex gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="h-10 w-24 animate-pulse rounded-full bg-paper-2" />
          ))}
        </div>
      </div>
      <StoryGridSkeleton />
    </PageFrame>
  );
}
