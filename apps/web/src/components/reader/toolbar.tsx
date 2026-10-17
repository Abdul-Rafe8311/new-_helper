"use client";

import { Download, Headphones, PanelLeft, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { pdfHref } from "@/lib/api";

import { AvatarMenu } from "./avatar-menu";
import { useChrome } from "./chrome-context";
import { ViewToggle } from "./view-toggle";

type ToolbarProps = { paperName: string; displayName: string; email: string };

/** Top bar: masthead, search, view toggle, PDF, the Listen slot, theme and the account menu. */
export function Toolbar({ paperName, displayName, email }: ToolbarProps) {
  const { query, setQuery, panelOpen, setPanelOpen, edition } = useChrome();
  const canDownload = Boolean(edition?.ready);

  // Sticky things below the toolbar (section tabs, the panel) need to know how tall it is.
  const bar = useRef<HTMLElement>(null);
  useEffect(() => {
    const element = bar.current;
    if (!element) return;
    const publish = () => document.documentElement.style.setProperty("--toolbar-h", `${element.offsetHeight}px`);
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <header ref={bar} className="sticky top-0 z-20 border-b border-rule bg-paper/95 backdrop-blur supports-[backdrop-filter]:bg-paper/80">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-2 px-3 py-2 sm:px-4">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Toggle sections panel"
          aria-expanded={panelOpen ?? undefined}
          onClick={() => setPanelOpen(panelOpen === true ? false : true)}
        >
          <PanelLeft aria-hidden="true" />
        </Button>

        <Link
          href="/today"
          className="min-w-0 truncate font-display text-lg font-black tracking-tight sm:text-xl"
        >
          {paperName}
        </Link>

        <div className="order-last flex w-full items-center gap-2 sm:order-none sm:ml-3 sm:w-auto sm:flex-1">
          <label className="relative block min-w-0 flex-1 sm:max-w-md">
            <span className="sr-only">Search this paper</span>
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted"
            />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search this paper"
              className="h-8 w-full rounded-md border border-rule bg-paper-2/50 pr-2 pl-8 font-sans text-sm outline-none placeholder:text-muted focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/40"
            />
          </label>
          <ViewToggle />
        </div>

        <div className="ml-auto flex items-center gap-1 sm:ml-0">
          {canDownload && edition ? (
            <Button asChild variant="outline" size="sm">
              <a href={pdfHref(edition.date)} download>
                <Download aria-hidden="true" />
                <span className="hidden lg:inline">Download PDF</span>
                <span className="sr-only lg:hidden">Download PDF</span>
              </a>
            </Button>
          ) : (
            <Button variant="outline" size="sm" disabled>
              <Download aria-hidden="true" />
              <span className="hidden lg:inline">Download PDF</span>
              <span className="sr-only lg:hidden">Download PDF</span>
            </Button>
          )}
          {/* Task 12 fills this slot with the audio edition. */}
          <div data-slot="listen">
            <Button variant="ghost" size="sm" disabled title="Listen is coming soon">
              <Headphones aria-hidden="true" />
              <span className="hidden lg:inline">Listen</span>
              <span className="sr-only lg:hidden">Listen (coming soon)</span>
            </Button>
          </div>
          <ThemeToggle />
          <AvatarMenu name={displayName} email={email} />
        </div>
      </div>
    </header>
  );
}
