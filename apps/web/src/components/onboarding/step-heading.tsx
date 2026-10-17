"use client";

import { useEffect, useRef } from "react";

import { FINALE } from "./machine";

/** Each step announces itself and takes focus, so keyboard and screen reader users follow along. */
export function StepHeading({
  step,
  title,
  lede,
}: {
  step: number;
  title: string;
  lede: string;
}) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    ref.current?.focus({ preventScroll: true });
  }, []);
  return (
    <header className="mb-6">
      <p className="kicker text-accent">{step >= FINALE ? "Going to press" : `Step ${step} of ${FINALE - 1}`}</p>
      <h2
        ref={ref}
        tabIndex={-1}
        className="mt-1 font-display text-3xl leading-tight font-black tracking-tight outline-none sm:text-4xl"
      >
        {title}
      </h2>
      <p className="mt-2 font-serif text-lg leading-snug text-muted">{lede}</p>
    </header>
  );
}
