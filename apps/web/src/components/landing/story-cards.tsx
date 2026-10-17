import type { CSSProperties } from "react";

import { sectionOf, type SampleStory } from "./sample-edition";

const META = "font-[variant-caps:all-small-caps] text-[13px] font-semibold tracking-wider";

/** Flat section-coloured stand-in, used because the sample edition carries no photographs. */
function Placeholder({ color, label }: { color: string; label: string }) {
  return (
    <div
      role="img"
      aria-label={`${label} section, no photo in this sample`}
      className="absolute inset-0 flex items-center justify-center bg-[var(--c)] font-[family-name:var(--font-figtree)] text-7xl font-black text-white/15 select-none"
      style={{ "--c": color } as CSSProperties}
    >
      <span aria-hidden="true">{label.slice(0, 1)}</span>
    </div>
  );
}

function Meta({ story, className = "" }: { story: SampleStory; className?: string }) {
  return (
    <p className={`${META} ${className}`}>
      {story.sources} sources · {story.hoursAgo}h ago
    </p>
  );
}

export function LeadCard({ story }: { story: SampleStory }) {
  const section = sectionOf(story.section);
  return (
    <article
      id={`story-${section.slug}`}
      className="relative min-h-[320px] scroll-mt-24 overflow-hidden rounded-2xl bg-[#2b2c22] sm:min-h-[420px]"
    >
      <Placeholder color={section.color} label={section.label} />
      <div className="absolute inset-0 bg-gradient-to-t from-[#1d1d1b] via-[#1d1d1b]/60 to-transparent" aria-hidden="true" />
      <div className="relative flex min-h-[inherit] flex-col justify-end p-5 sm:p-8">
        <p className="mb-2 text-xs font-bold tracking-[0.14em] text-[#FEE951] uppercase">{section.label}</p>
        <h3 className="max-w-3xl font-[family-name:var(--font-figtree)] text-3xl leading-[1.1] font-extrabold text-[#f4edda] sm:text-4xl">
          {story.headline}
        </h3>
        <p className="mt-3 max-w-2xl text-[15px] text-[#d9d3c0]">{story.summary}</p>
        <Meta story={story} className="mt-3 text-[#a8b89a]" />
      </div>
    </article>
  );
}

export function SupportCard({ story }: { story: SampleStory }) {
  const section = sectionOf(story.section);
  return (
    <article
      id={`story-${section.slug}`}
      className="flex scroll-mt-24 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#2b2c22]"
    >
      <div className="relative h-36">
        <Placeholder color={section.color} label={section.label} />
      </div>
      <div className="flex flex-1 flex-col p-4">
        <p className="mb-1 text-xs font-bold tracking-[0.14em] text-[#a8b89a] uppercase">{section.label}</p>
        <h3 className="font-[family-name:var(--font-figtree)] text-lg leading-snug font-bold text-[#f4edda]">{story.headline}</h3>
        <p className="mt-2 text-sm text-[#d9d3c0]">{story.summary}</p>
        <Meta story={story} className="mt-auto pt-3 text-[#a8b89a]" />
      </div>
    </article>
  );
}
