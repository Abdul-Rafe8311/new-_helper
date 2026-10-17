import Link from "next/link";

import { formatDateLine, Rule } from "@/components/paper";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import type { Session } from "@/lib/server/session";

import { LogoutButton } from "./logout-button";
import { NavLinks } from "./nav-links";

export function paperNameFor({ user, profile }: Session): string {
  return profile.paper_name || `The ${user.display_name.split(" ")[0]} Daily`;
}

/** Signed-in chrome: paper name, today's date in the reader's zone, nav, theme and sign out. */
export function AppHeader({ session, now, showNav = true }: { session: Session; now: Date; showNav?: boolean }) {
  return (
    <header className="mx-auto w-full max-w-6xl px-4 pt-3 sm:px-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <Link href="/today" className="block truncate font-display text-xl font-black tracking-tight sm:text-2xl">
            {paperNameFor(session)}
          </Link>
          <p className="font-sans text-[0.7rem] uppercase tracking-[0.12em] text-muted">
            {formatDateLine(now, session.user.timezone)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <ThemeToggle />
          <LogoutButton />
        </div>
      </div>
      {showNav ? <NavLinks /> : <div className="h-3" />}
      <Rule variant="double" />
    </header>
  );
}

export function AppHeaderSkeleton() {
  return (
    <div aria-hidden="true" className="mx-auto w-full max-w-6xl px-4 pt-3 sm:px-6">
      <div className="h-7 w-48 animate-pulse bg-paper-2" />
      <div className="mt-1.5 h-3 w-40 animate-pulse bg-paper-2" />
      <div className="h-10" />
      <Rule variant="double" />
    </div>
  );
}
