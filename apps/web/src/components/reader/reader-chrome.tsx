import type { ReactNode } from "react";

import type { Session } from "@/lib/server/session";

import { AmbientBackground } from "./ambient-background";
import { ChromeProvider } from "./chrome-context";
import { Masthead } from "./masthead";
import { ShellRoot } from "./shell-root";
import { TrackingProvider } from "./tracking-provider";

/** Today's date (YYYY-MM-DD) in the reader's time zone, which is what "today's paper" means. */
function localDate(timeZone: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

/** The signed-in frame: glow, masthead, and whichever page the reader is on. */
export function ReaderChrome({ session, children }: { session: Session; children: ReactNode }) {
  return (
    <ChromeProvider>
      <TrackingProvider>
        <ShellRoot>
          <a
            href="#main"
            className="sr-only z-50 bg-ink px-3 py-2 font-sans text-sm text-paper focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
          >
            Skip to the stories
          </a>
          <AmbientBackground />
          <Masthead
            displayName={session.user.display_name}
            email={session.user.email}
            pdfDate={localDate(session.user.timezone)}
          />
          {children}
        </ShellRoot>
      </TrackingProvider>
    </ChromeProvider>
  );
}

export function ReaderChromeSkeleton() {
  return (
    <div aria-hidden="true" className="min-h-screen bg-canvas">
      <div className="mx-auto flex h-16 max-w-[1680px] items-center px-4 sm:h-20 lg:h-[88px] lg:px-8">
        <div className="h-8 w-44 animate-pulse rounded bg-paper-2" />
      </div>
    </div>
  );
}
