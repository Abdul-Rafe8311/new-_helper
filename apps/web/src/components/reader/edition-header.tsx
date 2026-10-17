"use client";

import Link from "next/link";

import { cn } from "@/lib/utils";

import type { NavCategory } from "./side-nav";

/** Horizontally scrollable links to each category of the paper. */
export function TopicLinks({
  base,
  categories,
  activeSlug,
}: {
  base: string;
  categories: NavCategory[];
  activeSlug: string | null;
}) {
  if (categories.length === 0) return null;
  const item = (key: string, label: string, href: string, active: boolean) => (
    <li key={key} className="shrink-0">
      <Link
        href={href}
        scroll={false}
        aria-current={active ? "true" : undefined}
        className={cn(
          "nav-pill inline-flex min-h-10 items-center rounded-full px-4 font-sans text-[15px] font-semibold outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
          active ? "bg-cat/15 text-ink" : "text-muted hover:bg-cat/10 hover:text-ink",
        )}
      >
        {label}
      </Link>
    </li>
  );
  return (
    <nav aria-label="Topics" className="-mx-4 mt-4 sm:mx-0">
      <ul className="flex gap-1 overflow-x-auto px-4 pb-1 [scrollbar-width:none] sm:px-0">
        {item("all", "All", base, activeSlug === null)}
        {categories.map((c) => item(c.slug, c.label, `${base}?section=${c.slug}`, activeSlug === c.slug))}
      </ul>
    </nav>
  );
}

type EditionHeaderProps = {
  title: string;
  /** e.g. "Saturday 17 October" */
  dateLine: string;
  kicker?: string;
  note?: string | null;
  topics?: { base: string; categories: NavCategory[]; activeSlug: string | null };
};

/** A huge section title, the edition's date, and the topic links. */
export function EditionHeader({ title, dateLine, kicker, note, topics }: EditionHeaderProps) {
  return (
    <header className="pt-2 pb-6 sm:pt-4">
      <p className="font-sans text-[13px] font-semibold tracking-[0.08em] text-muted uppercase">
        {dateLine}
        {kicker ? <span> · {kicker}</span> : null}
      </p>
      <h1
        key={title}
        className="fade-swap mt-1 font-sans text-[clamp(2.25rem,6.2vw,4.5rem)] leading-[1.02] font-extrabold tracking-tight text-balance"
      >
        {title}
      </h1>
      {note ? <p className="mt-3 max-w-prose font-serif text-base text-muted italic">{note}</p> : null}
      {topics ? <TopicLinks {...topics} /> : null}
    </header>
  );
}
