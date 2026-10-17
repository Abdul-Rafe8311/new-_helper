"use client";

import { useEffect, useRef } from "react";

import { FINALE } from "./machine";

/** Each step announces itself and takes focus, so keyboard and screen reader users follow along. */
export function StepHeading({
  step,
  title,
  lede,
  why,
}: {
  step: number;
  title: string;
  lede: string;
  /** One honest sentence on how this step changes the reader's paper. */
  why?: string;
}) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    ref.current?.focus({ preventScroll: true });
  }, []);
  return (
    <header className="mb-8">
      <p className="kicker text-accent">{step >= FINALE ? "Going to press" : `Step ${step} of ${FINALE - 1}`}</p>
      <h2 ref={ref} tabIndex={-1} className="page-title mt-2 text-4xl outline-none sm:text-5xl">
        {title}
      </h2>
      <p className="lede mt-3 max-w-xl text-lg">{lede}</p>
      {why ? (
        <p className="mt-5 rounded-xl border border-rule bg-surface/70 px-4 py-3 font-sans text-sm leading-snug text-muted">
          <span className="kicker mr-2 text-ink">Shapes your paper</span>
          {why}
        </p>
      ) : null}
    </header>
  );
}
