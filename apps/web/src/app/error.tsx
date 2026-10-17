"use client";

import { StaticAmbient } from "@/components/brand/ambient";
import { Brand } from "@/components/brand/brand";
import { Button } from "@/components/ui/button";

/** Last-resort error screen: say what happened, offer a retry, keep the product's look. */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="brand-scope relative flex min-h-screen flex-col items-center justify-center bg-canvas px-6 text-center font-sans text-ink">
      <StaticAmbient />
      <div className="relative z-10 flex max-w-md flex-col items-center gap-4">
        <Brand size="lg" />
        <h1 className="page-title text-4xl sm:text-5xl">Something went wrong</h1>
        <p className="lede text-lg">We couldn&apos;t load this page. Your paper is safe; try again in a moment.</p>
        <Button variant="accent" size="lg" className="mt-2" onClick={reset}>
          Try again
        </Button>
      </div>
    </div>
  );
}
