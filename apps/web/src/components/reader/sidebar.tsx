"use client";

import { Archive, Bookmark, Newspaper, Settings, SlidersHorizontal, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

type Destination = { href: string; label: string; icon: LucideIcon; also?: string[] };

const DESTINATIONS: Destination[] = [
  { href: "/today", label: "Today", icon: Newspaper, also: ["/paper"] },
  { href: "/archive", label: "Archive", icon: Archive },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/interests", label: "Interests", icon: SlidersHorizontal },
  { href: "/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, { href, also = [] }: Destination): boolean {
  return [href, ...also].some((base) => pathname === base || pathname.startsWith(`${base}/`));
}

/**
 * Main navigation. A narrow icon rail fixed to the left on tablets and desktops; a bottom tab bar
 * on phones. The active destination takes the accent colour.
 */
export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className={cn(
        "fixed z-30 flex border-rule bg-paper",
        "inset-x-0 bottom-0 h-14 items-stretch justify-around border-t",
        "md:inset-y-0 md:right-auto md:h-auto md:w-[60px] md:flex-col md:items-center md:justify-start md:gap-1 md:border-t-0 md:border-r md:pt-3",
      )}
    >
      <Link
        href="/today"
        aria-hidden="true"
        tabIndex={-1}
        className="mb-3 hidden size-9 items-center justify-center font-display text-2xl font-black text-ink md:flex"
      >
        N
      </Link>
      {DESTINATIONS.map((destination) => {
        const active = isActive(pathname, destination);
        const Icon = destination.icon;
        return (
          <Link
            key={destination.href}
            href={destination.href}
            aria-label={destination.label}
            aria-current={active ? "page" : undefined}
            title={destination.label}
            className={cn(
              "relative flex flex-1 flex-col items-center justify-center gap-0.5 font-sans text-[0.625rem] transition-colors",
              "outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
              "md:size-11 md:flex-none md:rounded-md",
              active ? "text-accent md:bg-accent/10" : "text-muted hover:text-ink md:hover:bg-paper-2",
            )}
          >
            <Icon aria-hidden="true" className="size-5" strokeWidth={active ? 2.4 : 1.8} />
            <span className="md:sr-only">{destination.label}</span>
            {active ? (
              <span
                aria-hidden="true"
                className="absolute inset-x-4 top-0 h-0.5 bg-accent md:inset-x-auto md:top-2 md:bottom-2 md:left-0 md:h-auto md:w-0.5"
              />
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
