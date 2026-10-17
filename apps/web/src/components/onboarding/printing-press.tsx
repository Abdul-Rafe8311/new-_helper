"use client";

import { PixelScan } from "@/components/ui/pixel-scan";

const LINES = [92, 70, 100, 84, 58, 96, 76, 100, 64, 88];

type PrintingPressProps = {
  /** The current stage name, spelled out in pixels as the scan passes. */
  label?: string;
  /** 0..1 while printing; omit to loop while we do not know yet. */
  progress?: number;
  /** Nothing is printing (the run failed): show the page without the scan. */
  idle?: boolean;
};

/** A blank front page that the press scans line by line. Still when motion is reduced. */
export function PrintingPress({ label, progress, idle = false }: PrintingPressProps) {
  return (
    <div aria-hidden="true" data-testid="printing-press" className="relative mx-auto h-72 w-64 overflow-hidden rounded-sm border-2 border-ink bg-paper text-accent">
      <div className="space-y-2 px-4 pt-4">
        <div className="h-4 w-3/4 bg-ink" />
        <div className="h-px w-full bg-ink" />
        {LINES.map((width, i) => (
          <div key={i} className="h-1.5 bg-ink/35" style={{ width: `${width}%` }} />
        ))}
        <div className="h-3 w-2/3 bg-ink" />
        {LINES.slice(0, 6).map((width, i) => (
          <div key={`b${i}`} className="h-1.5 bg-ink/35" style={{ width: `${width}%` }} />
        ))}
      </div>
      <PixelScan className="absolute inset-0 h-full w-full" label={label} progress={progress} idle={idle} cell={6} />
    </div>
  );
}
