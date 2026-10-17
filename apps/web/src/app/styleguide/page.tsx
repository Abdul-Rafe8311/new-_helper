import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ArticleCard, Byline, Masthead, Rule, SectionHeader, WhyChip } from "@/components/paper";
import { MOCK_ARTICLES } from "@/components/paper/mock";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Styleguide" };

const SAMPLE_DATE = "2026-10-17T03:00:00Z";
const TOKENS = ["paper", "paper-2", "ink", "muted", "rule", "accent"] as const;

function Specimen({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="mt-10">
      <p className="kicker mb-3 text-muted">{label}</p>
      {children}
    </section>
  );
}

function Edition({ theme }: { theme: "light" | "dark" }) {
  return (
    <div
      data-theme-panel={theme}
      className={cn(theme, "bg-paper px-4 py-8 text-ink sm:px-8")}
    >
      <p className="kicker mb-6 text-accent">{theme === "light" ? "Morning edition · light" : "Night edition · dark"}</p>

      <Masthead
        paperName="The Morning Ledger"
        date={SAMPLE_DATE}
        editionNumber={12}
        weather="Lahore 24°C, haze"
        tagline="Made for Ada, from 43 sources"
      />

      <Specimen label="Tokens">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          {TOKENS.map((token) => (
            <div key={token} className="font-sans text-xs">
              <div className="h-12 border border-rule" style={{ background: `var(--${token})` }} />
              <p className="mt-1">{token}</p>
            </div>
          ))}
        </div>
      </Specimen>

      <Specimen label="Type">
        <p className="font-display text-4xl font-black">Fraunces for headlines</p>
        <p className="mt-2 max-w-prose font-serif text-lg">
          Source Serif 4 for reading. Long-form summaries sit in a comfortable measure with generous
          leading, the way a good broadsheet sets its columns.
        </p>
        <p className="mt-2 font-sans text-sm text-muted">Inter for interface chrome and metadata.</p>
      </Specimen>

      <Specimen label="Rules">
        <div className="space-y-4">
          <Rule variant="thin" />
          <Rule variant="thick" />
          <Rule variant="double" />
          <Rule variant="dotted" />
        </div>
      </Specimen>

      <Specimen label="Section header, byline, why chip">
        <SectionHeader title="World" description="What moved overnight" />
        <Byline source="Dawn" author="Sana Mir" publishedAt={SAMPLE_DATE} readingMinutes={4} />
        <div className="mt-3 flex flex-wrap gap-2">
          <WhyChip reason="You follow cricket" />
          <WhyChip reason="Trending in Lahore" />
        </div>
      </Specimen>

      <Specimen label="Buttons">
        <div className="flex flex-wrap gap-3">
          <Button variant="accent">Start my paper</Button>
          <Button>Primary</Button>
          <Button variant="outline">Try the demo</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
        </div>
      </Specimen>

      <Specimen label="Article cards: lead · feature · standard · brief · explore">
        <SectionHeader title="Front page" />
        <div className="grid gap-8 md:grid-cols-3 md:gap-0">
          <div className="md:col-span-2 md:pr-6">
            <ArticleCard variant="lead" article={MOCK_ARTICLES.lead} />
          </div>
          <div className="space-y-6 md:border-l md:border-rule md:pl-6">
            <ArticleCard variant="feature" article={MOCK_ARTICLES.feature} />
            <ArticleCard variant="explore" article={MOCK_ARTICLES.explore} />
          </div>
        </div>
        <Rule className="my-6" />
        <div className="grid gap-8 md:grid-cols-3 md:gap-0">
          <div className="md:col-span-2 md:pr-6">
            <ArticleCard variant="standard" article={MOCK_ARTICLES.standard} />
          </div>
          <div className="space-y-3 md:border-l md:border-rule md:pl-6">
            <p className="kicker text-muted">In brief</p>
            <ArticleCard variant="brief" article={MOCK_ARTICLES.brief} />
            <ArticleCard variant="brief" article={{ ...MOCK_ARTICLES.brief, id: "b2", headline: "PSL draft moved to next week" }} />
          </div>
        </div>
      </Specimen>
    </div>
  );
}

export default function StyleguidePage() {
  return (
    <main className="mx-auto w-full max-w-7xl">
      <div className="px-4 py-6 sm:px-8">
        <h1 className="font-display text-3xl font-bold">NewsHelper styleguide</h1>
        <p className="font-sans text-sm text-muted">Every paper component, in the morning (light) and night (dark) editions.</p>
      </div>
      <div className="grid xl:grid-cols-2">
        <Edition theme="light" />
        <Edition theme="dark" />
      </div>
    </main>
  );
}
