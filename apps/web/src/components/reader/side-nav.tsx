"use client";

import { Archive, Bookmark, Newspaper, Settings, SlidersHorizontal, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Dialog } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { useChrome } from "./chrome-context";

export type NavCategory = { slug: string; label: string; color: string };

type SideNavProps = {
  /** Where "For You" and the categories point, e.g. /today or /archive/2026-10-17. */
  base: string;
  categories?: NavCategory[];
};

const SECONDARY = [
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/archive", label: "Archive", icon: Archive },
  { href: "/interests", label: "Interests", icon: SlidersHorizontal },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

const PILL =
  "nav-pill flex items-center gap-3 rounded-full px-4 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

function NavList({ base, categories = [], onNavigate }: SideNavProps & { onNavigate?: () => void }) {
  const pathname = usePathname();
  const section = useSearchParams().get("section");
  const onFeed = pathname === base;
  const activeSlug = onFeed && categories.some((c) => c.slug === section) ? section : null;

  const primary = (key: string, label: string, href: string, active: boolean, color?: string): ReactNode => (
    <li key={key}>
      <Link
        href={href}
        scroll={false}
        aria-current={active ? "page" : undefined}
        onClick={onNavigate}
        style={color ? ({ "--pill": color } as React.CSSProperties) : undefined}
        className={cn(
          PILL,
          "py-2.5 text-[19px] leading-6 font-bold",
          active
            ? "bg-[color-mix(in_oklab,var(--pill,var(--cat))_15%,transparent)] text-ink"
            : "text-muted hover:bg-[color-mix(in_oklab,var(--pill,var(--cat))_10%,transparent)] hover:text-ink",
        )}
      >
        {label}
      </Link>
    </li>
  );

  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Categories">
        <ul className="space-y-1">
          {primary("for-you", "For You", base, onFeed && activeSlug === null)}
          {categories.map((c) => primary(c.slug, c.label, `${base}?section=${c.slug}`, activeSlug === c.slug, c.color))}
        </ul>
      </nav>
      <nav aria-label="Library" className="border-t border-rule pt-5">
        <ul className="space-y-0.5">
          {SECONDARY.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  onClick={onNavigate}
                  className={cn(
                    PILL,
                    "py-2 text-[15px] font-semibold",
                    active ? "bg-cat/10 text-ink" : "text-muted hover:bg-cat/10 hover:text-ink",
                  )}
                >
                  <Icon aria-hidden="true" className="size-4" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

/** Left navigation: 240px on desktop; a drawer behind the masthead's menu button below that. */
export function SideNav(props: SideNavProps) {
  const { menuOpen, setMenuOpen } = useChrome();
  return (
    <>
      <aside className="sticky top-6 hidden max-h-[calc(100vh-3rem)] w-60 shrink-0 self-start overflow-y-auto pr-4 pb-8 lg:block">
        <NavList {...props} />
      </aside>
      <Dialog.Root open={menuOpen} onOpenChange={setMenuOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/40 lg:hidden" />
          <Dialog.Content
            aria-describedby={undefined}
            className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] overflow-y-auto bg-canvas p-5 shadow-2xl outline-none lg:hidden"
          >
            <div className="mb-5 flex items-center justify-between">
              <Dialog.Title className="flex items-center gap-2 font-display text-xl font-black">
                <Newspaper aria-hidden="true" className="size-5" /> NewsHelper
              </Dialog.Title>
              <Dialog.Close className="inline-flex size-10 items-center justify-center rounded-full outline-none hover:bg-paper-2 focus-visible:ring-[3px] focus-visible:ring-ring/50" aria-label="Close menu">
                <X aria-hidden="true" className="size-5" />
              </Dialog.Close>
            </div>
            <NavList {...props} onNavigate={() => setMenuOpen(false)} />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
