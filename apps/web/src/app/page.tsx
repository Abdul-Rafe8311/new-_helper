import Link from "next/link";

import { DemoButton } from "@/components/auth/demo-button";
import { Rule } from "@/components/paper";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

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

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-16 sm:px-6">
      <div className="flex items-center justify-between py-3 font-sans text-[0.7rem] uppercase tracking-[0.12em] text-muted">
        <span>Vol. 1 · Personal edition</span>
        <div className="flex items-center gap-2">
          <Link href="/login" className="hover:text-ink">
            Sign in
          </Link>
          <ThemeToggle />
        </div>
      </div>
      <Rule />
      <header className="py-8 text-center sm:py-12">
        <h1 className="font-display text-6xl font-black leading-none tracking-tight sm:text-8xl">NewsHelper</h1>
        <p className="mt-4 font-serif text-xl italic text-muted sm:text-2xl">Your morning, on one page</p>
      </header>
      <Rule variant="double" />

      <section className="grid gap-8 py-10 md:grid-cols-[3fr_2fr] md:gap-0">
        <div className="md:border-r md:border-rule md:pr-8">
          <p className="kicker text-accent">Today&apos;s lead</p>
          <h2 className="mt-2 font-display text-3xl font-black leading-tight sm:text-4xl">
            A newspaper that learns what you care about.
          </h2>
          <p className="mt-4 font-serif text-lg leading-relaxed">
            NewsHelper gathers the day&apos;s stories from across the web and composes one personal
            paper, in proper newspaper style. Click through to the originals, skip what you don&apos;t
            want, keep every edition in your archive.
          </p>
          <div className="mt-6 flex flex-wrap items-start gap-3">
            <Button asChild variant="accent" size="lg">
              <Link href="/signup">Start my paper</Link>
            </Button>
            <DemoButton />
          </div>
        </div>
        <aside aria-labelledby="how-it-works" className="md:pl-8">
          <h2 id="how-it-works" className="kicker border-b-[3px] border-ink pb-1.5">
            How it works
          </h2>
          <ol className="mt-4 space-y-5">
            {STEPS.map((step, i) => (
              <li key={step.title} className="flex gap-4">
                <span className="font-display text-3xl font-black leading-none text-accent">{i + 1}</span>
                <div>
                  <h3 className="font-display text-lg font-bold leading-snug">{step.title}</h3>
                  <p className="mt-1 font-serif text-[0.95rem] leading-relaxed text-muted">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </aside>
      </section>
    </main>
  );
}
