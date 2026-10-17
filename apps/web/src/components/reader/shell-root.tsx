"use client";

import type { CSSProperties, ReactNode } from "react";

import { useChrome } from "./chrome-context";

/** The page canvas. Exposes the category colour as `--cat` to everything inside it. */
export function ShellRoot({ children }: { children: ReactNode }) {
  const { accent } = useChrome();
  return (
    <div
      className="relative flex min-h-screen flex-col bg-canvas font-sans text-ink"
      style={{ "--cat": accent } as CSSProperties}
    >
      {children}
    </div>
  );
}
