import type { CSSProperties } from "react";

import { SAMPLE_KEY_FACTS, SAMPLE_PHONE_ROWS, SAMPLE_STORIES, sectionOf } from "./sample-edition";

const TILE = "bg-[var(--c)]";

/** Flat section-coloured thumbnail: the sample edition carries no photographs. */
function Thumb({ section, className }: { section: string; className: string }) {
  return <div className={`${TILE} shrink-0 rounded-md ${className}`} style={{ "--c": sectionOf(section).color } as CSSProperties} />;
}

function Tablet() {
  const [selected] = SAMPLE_STORIES;
  return (
    <div className="hidden w-[560px] rounded-[28px] border border-white/15 bg-[#121211] p-3 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)] md:block">
      <div className="flex h-[340px] overflow-hidden rounded-[18px] bg-[#1d1d1b]">
        <div className="min-w-0 flex-1 border-r border-white/10 p-3">
          <p className="mb-2 px-1 text-[11px] font-bold tracking-[0.14em] text-[#a8b89a] uppercase">Today</p>
          <ul className="space-y-1.5">
            {SAMPLE_STORIES.map((story, i) => (
              <li
                key={story.id}
                className={`flex items-center gap-2.5 rounded-lg border-l-[3px] p-2 ${
                  i === 0 ? "border-[#FEE951] bg-[#FEE951]/10" : "border-transparent bg-white/[0.03]"
                }`}
              >
                <Thumb section={story.section} className="size-11" />
                <div className="min-w-0">
                  <p className="truncate text-[12.5px] font-bold text-[#f4edda]">{story.headline}</p>
                  <p className="truncate text-[11px] text-[#d9d3c0]">{story.summary}</p>
                  <p className="mt-0.5 text-[10px] font-semibold text-[#a8b89a]">
                    {story.source} · {story.readMins} min read
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="w-[190px] shrink-0 bg-[#2b2c22] py-4 pr-14 pl-4">
          <p className="text-[10px] font-bold tracking-[0.14em] text-[#a8b89a] uppercase">{sectionOf(selected.section).label}</p>
          <p className="mt-1 text-[14px] leading-snug font-extrabold text-[#f4edda]">{selected.headline}</p>
          <p className="mt-2 text-[11.5px] text-[#d9d3c0]">{selected.summary}</p>
          <ul className="mt-3 space-y-2">
            {SAMPLE_KEY_FACTS.map((fact) => (
              <li key={fact} className="rounded-md bg-[#6b7048]/40 px-2 py-1.5 text-[11px] font-semibold text-[#f4edda]">
                {fact}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Phone() {
  return (
    <div className="mx-auto w-[210px] rounded-[34px] border border-white/20 bg-[#121211] p-2.5 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)] md:absolute md:-right-2 md:-bottom-8 md:mx-0">
      <div className="h-[330px] overflow-hidden rounded-[26px] bg-[#1d1d1b] p-3">
        <div className="mx-auto mb-3 h-1.5 w-14 rounded-full bg-white/15" />
        <p className="mb-2 font-[family-name:var(--font-figtree)] text-[15px] font-extrabold text-[#f4edda]">Your morning</p>
        {SAMPLE_PHONE_ROWS.map((row) => (
          <section key={row.section} className="mb-4">
            <p className="mb-1.5 text-[10px] font-bold tracking-[0.14em] text-[#a8b89a] uppercase">{sectionOf(row.section).label}</p>
            <ul className="grid grid-cols-3 gap-1.5">
              {row.tiles.map((title) => (
                <li key={title}>
                  <Thumb section={row.section} className="aspect-[3/4] w-full" />
                  <p className="mt-1 text-[9.5px] leading-tight font-semibold text-[#d9d3c0]">{title}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

/**
 * A CSS-drawn tablet and phone showing the sample edition. Purely decorative: hidden from assistive
 * tech and inert, so nothing inside can take focus. Below 768px only the phone is shown.
 */
export function DevicePreview() {
  return (
    <figure className="mt-8 mb-2">
      <div aria-hidden="true" {...{ inert: true }} className="pointer-events-none relative mx-auto pb-8 md:h-[420px] md:w-[720px] md:pb-0">
        <Tablet />
        <Phone />
      </div>
      <figcaption className="mt-2 text-center text-xs font-bold tracking-[0.14em] text-[#a8b89a] uppercase">
        Sample edition · preview
      </figcaption>
    </figure>
  );
}
