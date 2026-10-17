import Link from "next/link";

import { StaticAmbient } from "@/components/brand/ambient";
import { Brand } from "@/components/brand/brand";
import { Button } from "@/components/ui/button";

/** An unknown address: same canvas, wordmark and primary action as everywhere else. */
export default function NotFound() {
  return (
    <div className="brand-scope relative flex min-h-screen flex-col items-center justify-center bg-canvas px-6 text-center font-sans text-ink">
      <StaticAmbient />
      <div className="relative z-10 flex max-w-md flex-col items-center gap-4">
        <Brand size="lg" />
        <p className="kicker text-accent">Error 404</p>
        <h1 className="page-title text-4xl sm:text-5xl">That page is not in today&apos;s paper</h1>
        <p className="lede text-lg">The link may be old, or the address mistyped.</p>
        <Button asChild variant="accent" size="lg" className="mt-2">
          <Link href="/">Back to the front page</Link>
        </Button>
      </div>
    </div>
  );
}
