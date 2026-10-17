"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState, type CSSProperties, type KeyboardEvent } from "react";

import { MASCOTS, Portrait } from "./mascots";
import { SAMPLE_SECTION_COLORS, SAMPLE_STORIES } from "./sample";

const CARDS = SAMPLE_STORIES.map((story) => {
  const index = MASCOTS.findIndex((m) => m.label === story.section);
  return { story, mascot: MASCOTS[index], index };
}).filter((card) => card.mascot);

/**
 * Expandable desk cards: one card per section of the sample edition. A card opens in place (its
 * neighbours keep their size), and only the card's own button is focusable until it is open.
 */
export function DeskCards() {
  const [open, setOpen] = useState<string | null>(null);
  const base = useId();

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape" && open) setOpen(null);
  };

  return (
    <section id="desks" className="lp-desks" aria-labelledby="lp-desks-title">
      <h2 id="lp-desks-title">Every desk, one edition</h2>
      <p className="lp-desks__lede">Open a desk to see how a story sits in your paper.</p>
      <ul className="lp-cards">
        {CARDS.map(({ story, mascot, index }) => {
          const isOpen = open === story.id;
          const panelId = `${base}-${story.id}`;
          return (
            <li key={story.id}>
              <article
                className="lp-card"
                data-open={isOpen}
                style={{ "--c": SAMPLE_SECTION_COLORS[story.section] } as CSSProperties}
                onKeyDown={onKeyDown}
              >
                <button
                  type="button"
                  className="lp-card__btn"
                  aria-expanded={isOpen}
                  aria-controls={panelId}
                  onClick={() => setOpen(isOpen ? null : story.id)}
                >
                  <span className="lp-card__img" aria-hidden="true">
                    <span className="lp-card__tile">
                      <Portrait mascot={mascot} index={index} />
                    </span>
                  </span>
                  <span className="lp-card__title">{story.section}</span>
                  <span className="lp-card__desc">{story.headline}</span>
                  <ChevronDown aria-hidden="true" className="lp-card__chev" />
                </button>
                <div id={panelId} className="lp-card__more" inert={!isOpen}>
                  <div>
                    <p>{story.summary}</p>
                    <p className="lp-card__meta">
                      {story.source} · {story.sources} sources · {story.readMins} min read
                    </p>
                  </div>
                </div>
              </article>
            </li>
          );
        })}
      </ul>
      <p className="lp-sample">Sample edition</p>
    </section>
  );
}
