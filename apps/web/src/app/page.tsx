import Link from "next/link";

import { CurrentYear } from "@/components/landing/current-year";
import { LandingShell } from "@/components/landing/landing-shell";
import { SAMPLE_SECTIONS, SAMPLE_STORIES } from "@/components/landing/sample-edition";
import { LeadCard, SupportCard } from "@/components/landing/story-cards";

const REPO_URL = "https://github.com/Abdul-Rafe8311/new-_helper";

const STEPS = [
  {
    title: "Tell us what you care about",
    body: "Pick topics, teams, companies and places in a two-minute onboarding. Skip what bores you.",
  },
  {
    title: "We read the web overnight",
    body: "Hundreds of trusted sources are gathered, de-duplicated and summarised before you wake up.",
  },
  {
    title: "Your paper, every morning",
    body: "One front page made for you. Read it on the web or download the PDF. It gets better as you read.",
  },
] as const;

const FOCUS = "outline-none focus-visible:ring-[3px] focus-visible:ring-[#FEE951]/70";

export default function Home() {
  const [lead, ...rest] = SAMPLE_STORIES;
  return (
    <div className="landing flex-1 bg-gradient-to-b from-[#1d1d1b] to-[#2b2c22] text-[#f4edda] [font-family:var(--font-inter),system-ui,sans-serif]">
      <LandingShell>
        <main className="pb-16">
          <section id="sample-edition" aria-labelledby="landing-title" className="scroll-mt-24 pt-8 sm:pt-12">
            <h1
              id="landing-title"
              className="font-[family-name:var(--font-figtree)] text-4xl leading-[1.05] font-extrabold tracking-tight sm:text-6xl"
            >
              Your morning, on one page
            </h1>
            <p className="mt-3 max-w-xl text-[#d9d3c0]">
              NewsHelper gathers the day&apos;s stories from across the web and composes one personal paper.
            </p>
            <ul aria-label="Topics in the sample edition" className="mt-5 flex flex-wrap gap-2">
              {SAMPLE_SECTIONS.map((s) => (
                <li key={s.slug}>
                  <a
                    href={`#story-${s.slug}`}
                    className={`inline-flex min-h-11 items-center rounded-full border border-[#a8b89a]/40 bg-[#a8b89a]/10 px-4 text-sm font-semibold text-[#e5e8d8] hover:bg-[#a8b89a]/20 ${FOCUS}`}
                  >
                    {s.label}
                  </a>
                </li>
              ))}
            </ul>
            <p className="mt-6 text-xs font-bold tracking-[0.14em] text-[#a8b89a] uppercase">Sample edition</p>
            <div className="mt-2 grid gap-4 sm:grid-cols-3">
              <div className="sm:col-span-3">
                <LeadCard story={lead} />
              </div>
              {rest.map((story) => (
                <SupportCard key={story.id} story={story} />
              ))}
            </div>
          </section>

          <section aria-labelledby="how-it-works" className="mt-14 rounded-2xl border border-white/10 bg-[#6b7048]/20 p-6 sm:p-8">
            <h2 id="how-it-works" className="font-[family-name:var(--font-figtree)] text-2xl font-extrabold">
              How it works
            </h2>
            <ol className="mt-5 grid gap-6 md:grid-cols-3">
              {STEPS.map((step, i) => (
                <li key={step.title} className="flex gap-4">
                  <span aria-hidden="true" className="font-[family-name:var(--font-figtree)] text-4xl leading-none font-black text-[#a8b89a]">
                    {i + 1}
                  </span>
                  <div>
                    <h3 className="font-[family-name:var(--font-figtree)] text-lg font-bold">{step.title}</h3>
                    <p className="mt-1 text-sm text-[#d9d3c0]">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </main>
        <footer className="flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-white/10 py-6 text-sm text-[#d9d3c0]">
          <a href={REPO_URL} className={`inline-flex min-h-11 items-center underline-offset-4 hover:underline ${FOCUS}`}>
            GitHub
          </a>
          <a href={`${REPO_URL}#readme`} className={`inline-flex min-h-11 items-center underline-offset-4 hover:underline ${FOCUS}`}>
            README
          </a>
          <Link href="/login" className={`inline-flex min-h-11 items-center underline-offset-4 hover:underline ${FOCUS}`}>
            Sign in
          </Link>
          <span className="ml-auto">© <CurrentYear /> NewsHelper</span>
        </footer>
      </LandingShell>
    </div>
  );
}
