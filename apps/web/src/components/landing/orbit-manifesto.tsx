"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { MASCOTS, Portrait } from "./mascots";

const PRODUCT = "NewsHelper";
const STATEMENT = `${PRODUCT} brings the stories you care about into one daily edition. Choose your interests. Read articles from different sources. Save a newspaper PDF. Tell us what to show more or less of next time.`;
const WORDS = STATEMENT.split(" ");

/**
 * Where each portrait drifts to as the orbit breaks apart: offsets from the stage centre in vw/svh,
 * a depth scale and an opacity. Fixed numbers, so server and client always agree. They hug the left
 * and right margins, away from the centred statement.
 */
const SCATTER: readonly { x: number; y: number; s: number; o: number }[] = [
  { x: -41, y: -34, s: 1.35, o: 0.7 },
  { x: 38, y: -38, s: 0.8, o: 0.4 },
  { x: -30, y: -12, s: 0.7, o: 0.35 },
  { x: 43, y: -18, s: 1.5, o: 0.75 },
  { x: -44, y: 8, s: 1.1, o: 0.6 },
  { x: 34, y: 4, s: 0.65, o: 0.3 },
  { x: -36, y: 30, s: 1.6, o: 0.8 },
  { x: 40, y: 26, s: 0.9, o: 0.5 },
  { x: -22, y: -40, s: 0.6, o: 0.3 },
  { x: 28, y: -26, s: 1.2, o: 0.55 },
  { x: -45, y: -22, s: 0.85, o: 0.45 },
  { x: 44, y: 38, s: 1.3, o: 0.65 },
  { x: -28, y: 40, s: 0.75, o: 0.35 },
  { x: 30, y: 42, s: 0.7, o: 0.3 },
  { x: -47, y: -4, s: 0.95, o: 0.5 },
  { x: 45, y: 8, s: 1.05, o: 0.55 },
];

const clamp = (n: number) => Math.min(1, Math.max(0, n));

/**
 * Sections 1 and 2 share one decorative cast layer, so the orbit visibly breaks apart into the
 * manifesto instead of being swapped for a second set of portraits. Scrolling updates two CSS
 * custom properties per frame (--p on the layer, --r on the statement); React does not re-render.
 */
export function OrbitManifesto() {
  const stageRef = useRef<HTMLDivElement>(null);
  const layerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const statementRef = useRef<HTMLParagraphElement>(null);
  const [pinned, setPinned] = useState<string | null>(null);

  useEffect(() => {
    const stage = stageRef.current;
    const layer = layerRef.current;
    const list = listRef.current;
    const statement = statementRef.current;
    if (!stage || !layer || !list || !statement) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let lastP = -1;
    let lastR = -1;
    let scattered = false;

    const reset = () => {
      layer.style.removeProperty("--p");
      statement.style.removeProperty("--r");
      layer.dataset.scattered = "false";
      list.inert = false;
      lastP = -1;
      lastR = -1;
      scattered = false;
    };

    const update = () => {
      frame = 0;
      if (reduce.matches) return;
      const vh = window.innerHeight;
      const raw = clamp(-stage.getBoundingClientRect().top / (vh * 0.8));
      const p = raw * raw * (3 - 2 * raw);
      if (Math.abs(p - lastP) > 0.001) {
        layer.style.setProperty("--p", p.toFixed(3));
        lastP = p;
      }
      const isScattered = p > 0.5;
      if (isScattered !== scattered) {
        scattered = isScattered;
        layer.dataset.scattered = String(isScattered);
        list.inert = isScattered; // portraits that have drifted behind the text leave the tab order
      }
      const box = statement.getBoundingClientRect();
      const r = clamp((vh * 0.85 - box.top) / (box.height + vh * 0.4));
      if (Math.abs(r - lastR) > 0.002) {
        statement.style.setProperty("--r", r.toFixed(3));
        lastR = r;
      }
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const onMotionChange = () => {
      if (reduce.matches) reset();
      else schedule();
    };

    const observer = new IntersectionObserver(([entry]) => {
      layer.dataset.offscreen = String(!entry.isIntersecting);
    });
    observer.observe(stage);
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    reduce.addEventListener("change", onMotionChange);
    schedule();
    return () => {
      if (frame) cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      reduce.removeEventListener("change", onMotionChange);
    };
  }, []);

  return (
    <div className="lp-stage" ref={stageRef}>
      <section id="top" className="lp-hero" aria-labelledby="lp-title">
        <h1 id="lp-title">
          Your world.{" "}
          <br />
          One daily paper.
        </h1>
        <p className="lp-hero__copy">Stories around your interests. Read your edition online, or take the newspaper PDF with you.</p>
        <Link href="/signup" className="lp-pill lp-pill--primary">
          Build my paper
        </Link>
        <p className="lp-hero__meta">Read online · Download the PDF · Keep past editions</p>
        <p className="lp-hero__corner">
          <strong>Your reading, together</strong>
          <span>Interests · Sources · Daily edition</span>
        </p>
      </section>

      <div className="lp-castwrap">
        <div className="lp-cast" ref={layerRef} data-paused="false">
          <ul
            ref={listRef}
            aria-label="Topic desks"
            style={{ listStyle: "none", margin: 0, padding: 0 }}
            onFocus={() => {
              if (layerRef.current) layerRef.current.dataset.focus = "true";
            }}
            onBlur={(e) => {
              if (layerRef.current && !listRef.current?.contains(e.relatedTarget)) layerRef.current.dataset.focus = "false";
            }}
          >
            {MASCOTS.map((mascot, i) => {
              const s = SCATTER[i];
              const style = {
                "--a": `${(360 / MASCOTS.length) * i - 90}deg`,
                "--sx": `${s.x}vw`,
                "--sy": `${s.y}svh`,
                "--ss": s.s,
                "--so": s.o,
              } as CSSProperties;
              const open = pinned === mascot.slug;
              return (
                <li key={mascot.slug} className="lp-slot" style={style}>
                  <button
                    type="button"
                    className="lp-tile"
                    aria-pressed={open}
                    aria-label={`${mascot.label} desk`}
                    onClick={() => setPinned(open ? null : mascot.slug)}
                    onBlur={() => open && setPinned(null)}
                  >
                    <Portrait mascot={mascot} index={i} />
                    <span className="lp-label" aria-hidden="true">
                      {mascot.label} desk
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      <section id="how-it-works" className="lp-manifesto" aria-label="How it works">
        <p
          className="lp-statement"
          ref={statementRef}
          style={{ "--n": WORDS.length } as CSSProperties}
        >
          <span className="lp-sr">{STATEMENT}</span>
          <span aria-hidden="true">
            {WORDS.map((word, i) => (
              <span key={i} className="lp-word" style={{ "--i": i } as CSSProperties}>
                {word}{" "}
              </span>
            ))}
          </span>
        </p>
      </section>
    </div>
  );
}
