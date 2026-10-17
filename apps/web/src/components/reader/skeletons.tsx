import { cn } from "@/lib/utils";

function Bar({ className }: { className?: string }) {
  return <div className={cn("animate-pulse bg-paper-2", className)} />;
}

function CardSkeleton() {
  return (
    <div className="space-y-3">
      <div className="halftone aspect-[16/9] w-full animate-pulse opacity-70" />
      <Bar className="h-3 w-20" />
      <Bar className="h-6 w-11/12" />
      <Bar className="h-6 w-2/3" />
      <Bar className="h-3 w-full" />
      <Bar className="h-3 w-10/12" />
    </div>
  );
}

/** Newspaper-shaped placeholder shown while an edition loads. */
export function ReaderSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading your paper" role="status" className="flex flex-1 items-stretch">
      <div className="hidden w-[260px] shrink-0 space-y-3 border-r border-rule p-4 lg:block">
        <Bar className="h-6 w-40" />
        <Bar className="h-3 w-32" />
        <div className="h-px bg-rule" />
        {Array.from({ length: 7 }, (_, i) => (
          <Bar key={i} className="h-7 w-full" />
        ))}
      </div>
      <div className="min-w-0 flex-1 px-4 pt-4 pb-16 sm:px-6">
        <Bar className="h-3 w-48" />
        <Bar className="mt-3 h-9 w-72 max-w-full" />
        <div className="mt-2 h-1 border-y border-ink/60" />
        <div className="mt-6 grid gap-x-6 gap-y-8 sm:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <span className="sr-only">Loading your paper…</span>
      </div>
    </div>
  );
}
