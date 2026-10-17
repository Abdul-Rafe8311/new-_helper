"use client";

import { Plus } from "lucide-react";
import { useId, useState } from "react";

const QUESTIONS = [
  {
    q: "What is NewsHelper?",
    a: "A personal morning newspaper. It learns what you care about, gathers articles from across the web each day, and puts them into one edition made for you.",
  },
  {
    q: "How do I choose what I read?",
    a: "A short onboarding asks for your topics, teams, companies and places, and you can skip anything that bores you. You can change your interests later.",
  },
  {
    q: "Can I read it offline or on paper?",
    a: "Each edition has a newspaper-style PDF with its images that you can download. You can also read the same edition in your browser.",
  },
  {
    q: "Can I go back to an earlier edition?",
    a: "Yes. Your archive keeps past editions so you can reopen one when you want to return to a story.",
  },
  {
    q: "How does it get better over time?",
    a: "Save, skip, or tell us to show more or less of something. That feedback shapes your next editions, and your interests page shows what the paper has learned.",
  },
  {
    q: "Do I read the original articles?",
    a: "Every story links back to the original article from its source, so you can click through and read the full piece.",
  },
] as const;

/** A plain disclosure list: one question open at a time, each answer hidden from keyboard and AT when closed. */
export function Faq() {
  const [open, setOpen] = useState<number | null>(null);
  const base = useId();
  return (
    <section id="faq" className="lp-faq" aria-labelledby="lp-faq-title">
      <h2 id="lp-faq-title">Frequently asked questions</h2>
      <ul className="lp-faq__list">
        {QUESTIONS.map(({ q, a }, i) => {
          const isOpen = open === i;
          return (
            <li key={q} data-open={isOpen}>
              <h3>
                <button
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={`${base}-${i}`}
                  onClick={() => setOpen(isOpen ? null : i)}
                >
                  <Plus aria-hidden="true" />
                  <span>{q}</span>
                </button>
              </h3>
              <div id={`${base}-${i}`} className="lp-faq__answer" inert={!isOpen}>
                <p>{a}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
