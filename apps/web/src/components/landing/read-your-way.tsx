"use client";

import { Archive, ArrowRight, Bookmark, Download, FileText, Newspaper, ThumbsDown, ThumbsUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { PixelScan } from "@/components/ui/pixel-scan";

import { SAMPLE_ARCHIVE_DATES, SAMPLE_DATE, SAMPLE_SECTION_COLORS, SAMPLE_STORIES } from "./sample";

const VIEWS = [
  { id: "web", label: "Web edition", Icon: Newspaper },
  { id: "pdf", label: "Newspaper PDF", Icon: FileText },
  { id: "archive", label: "Archive", Icon: Archive },
] as const;

const color = (section: string) => ({ "--c": SAMPLE_SECTION_COLORS[section] }) as CSSProperties;
const [LEAD, ...MORE] = SAMPLE_STORIES;

function WebPanel() {
  return (
    <>
      <div className="lp-wb__head">
        <strong>NewsHelper</strong>
        <span>{SAMPLE_DATE.replace(/ \d{4}$/, "")}</span>
      </div>
      <p className="lp-wb__title">Your morning paper</p>
      <div className="lp-tags">
        <span className="lp-tag" data-on="true">For you</span>
        {["Technology", "Science", "Business"].map((t) => (
          <span key={t} className="lp-tag">{t}</span>
        ))}
      </div>
      <div className="lp-wb__lead">
        <div className="lp-photo" style={color(LEAD.section)} />
        <div>
          <p className="lp-kicker">{LEAD.section} · {LEAD.source}</p>
          <h3>{LEAD.headline}</h3>
          <p className="lp-sum">{LEAD.summary}</p>
          <div className="lp-actions">
            <Bookmark aria-hidden="true" />
            <ThumbsUp aria-hidden="true" />
            <ThumbsDown aria-hidden="true" />
          </div>
        </div>
      </div>
      <div className="lp-mini">
        {MORE.slice(0, 2).map((s) => (
          <div key={s.id}>
            <div className="lp-photo" style={color(s.section)} />
            <div>
              <h3>{s.headline}</h3>
              <p>{s.source} · {s.readMins} min</p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function PdfPanel() {
  return (
    <>
      <div className="lp-pdf__page">
        <div className="lp-pdf__mast">
          <strong>NewsHelper</strong>
          <span>Curated for you · {SAMPLE_DATE}</span>
        </div>
        <div className="lp-pdf__lead">
          <div className="lp-photo" style={color(LEAD.section)} />
          <h3>{LEAD.headline}</h3>
          <p>{LEAD.summary}</p>
        </div>
        <div className="lp-pdf__cols">
          {MORE.slice(0, 2).map((s) => (
            <div key={s.id}>
              <div className="lp-photo" style={color(s.section)} />
              <h4>{s.headline}</h4>
              <div className="lp-bars" aria-hidden="true"><i /><i /><i /><i /></div>
            </div>
          ))}
        </div>
        <div className="lp-pdf__brief">
          <h4>{MORE[2].headline}</h4>
          <div className="lp-bars" aria-hidden="true"><i /><i /><i /></div>
        </div>
      </div>
      <div className="lp-pdf__get">
        <Download aria-hidden="true" /> Download PDF
      </div>
    </>
  );
}

function ArchivePanel() {
  return (
    <div className="lp-ar">
      <h3>Past editions</h3>
      <ul>
        <li data-today="true">
          {SAMPLE_DATE.replace(/ \d{4}$/, "")}
          <span>{SAMPLE_STORIES.length} stories</span>
        </li>
        {SAMPLE_ARCHIVE_DATES.map((d) => (
          <li key={d}>
            {d.replace(/ \d{4}$/, "")}
            <span>Sample</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const PANELS = { web: <WebPanel />, pdf: <PdfPanel />, archive: <ArchivePanel /> } as const;

/**
 * Section 3. On desktop the section is taller than the screen and its stage is `position: sticky`,
 * so native scrolling advances the three previews. Chips are real buttons: choosing one wins until
 * the reader scrolls again. Below 768px (or with reduced motion) nothing is pinned.
 */
export function ReadYourWay() {
  const [active, setActive] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);
  const manual = useRef<number | null>(null); // scrollY at the moment a chip was chosen

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
    const pinned = window.matchMedia("(min-width: 768px) and (prefers-reduced-motion: no-preference)");
    let frame = 0;
    let current = 0;
    const update = () => {
      frame = 0;
      if (!pinned.matches) return;
      if (manual.current !== null) {
        if (Math.abs(window.scrollY - manual.current) < 12) return;
        manual.current = null;
      }
      const box = section.getBoundingClientRect();
      const span = box.height - window.innerHeight;
      if (span <= 0) return;
      const progress = Math.min(0.9999, Math.max(0, -box.top / span));
      const next = Math.floor(progress * VIEWS.length);
      if (next !== current) {
        current = next;
        setActive(next);
      }
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    schedule();
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, []);

  const choose = (index: number) => {
    manual.current = window.scrollY;
    setActive(index);
  };

  return (
    <section id="read-your-way" className="lp-ryw" ref={sectionRef} aria-labelledby="lp-ryw-title">
      <div className="lp-ryw__pin">
        <div className="lp-ryw__left">
          <h2 id="lp-ryw-title">Read your way</h2>
          <div className="lp-chips" role="group" aria-label="Choose a preview">
            {VIEWS.map(({ id, label, Icon }, i) => (
              <button
                key={id}
                type="button"
                className="lp-chip"
                aria-pressed={active === i}
                aria-controls={`lp-panel-${id}`}
                onClick={() => choose(i)}
              >
                <Icon aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>
          <p className="lp-ryw__body">
            Read today&apos;s edition in your browser. Download the newspaper PDF. Open an older edition when you want to return
            to a story.
          </p>
          <Link href="/today" className="lp-pill lp-pill--dark">
            Open my paper <ArrowRight aria-hidden="true" size={14} />
          </Link>
          <p className="lp-sample">Sample edition · {SAMPLE_DATE}</p>
        </div>
        <div className="lp-ryw__phone">
          <div className="lp-phone">
            <div className="lp-phone__screen">
              <span className="lp-notch" aria-hidden="true" />
              <PixelScan className="lp-scan" trigger={active} label={VIEWS[active].label.toUpperCase()} cell={5} />
              {VIEWS.map(({ id, label }, i) => (
                <div
                  key={id}
                  id={`lp-panel-${id}`}
                  role="group"
                  aria-label={`${label} preview`}
                  className="lp-panel"
                  data-active={active === i}
                  aria-hidden={active !== i}
                  inert={active !== i}
                >
                  {PANELS[id]}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
