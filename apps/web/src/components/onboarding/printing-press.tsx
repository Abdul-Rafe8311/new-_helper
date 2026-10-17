"use client";

import { motion, useReducedMotion } from "framer-motion";

const LINES = [92, 70, 100, 84, 58, 96, 76, 100, 64, 88];

/** A little press: rollers turn while a fresh page feeds out. Static when motion is reduced. */
export function PrintingPress() {
  const reduceMotion = useReducedMotion();
  const spin = (reverse: boolean) =>
    reduceMotion
      ? undefined
      : { rotate: reverse ? -360 : 360, transition: { duration: 1.6, ease: "linear" as const, repeat: Infinity } };

  return (
    <div aria-hidden="true" data-testid="printing-press" className="relative mx-auto h-64 w-60">
      <div className="absolute inset-x-0 top-0 z-10 flex h-20 items-center justify-center gap-5 rounded-sm border-2 border-ink bg-paper-2">
        {[false, true].map((reverse) => (
          <motion.div
            key={String(reverse)}
            animate={spin(reverse)}
            className="relative size-14 rounded-full border-2 border-ink bg-paper"
          >
            <span className="absolute inset-x-1/2 top-1 bottom-1 w-0.5 -translate-x-1/2 bg-ink/60" />
            <span className="absolute inset-y-1/2 left-1 right-1 h-0.5 -translate-y-1/2 bg-ink/60" />
          </motion.div>
        ))}
      </div>

      <div className="absolute inset-x-6 top-[4.75rem] bottom-0 overflow-hidden">
        <motion.div
          animate={reduceMotion ? undefined : { y: [-60, 0] }}
          transition={reduceMotion ? undefined : { duration: 1.6, ease: "linear", repeat: Infinity }}
          className="space-y-2 border-x border-b border-ink bg-paper px-3 pt-3 pb-6 shadow-sm"
        >
          <div className="h-3 w-3/4 bg-ink" />
          <div className="h-px w-full bg-ink" />
          {LINES.map((width, i) => (
            <div key={i} className="h-1.5 bg-ink/35" style={{ width: `${width}%` }} />
          ))}
          <div className="h-3 w-2/3 bg-ink" />
          {LINES.slice(0, 5).map((width, i) => (
            <div key={`b${i}`} className="h-1.5 bg-ink/35" style={{ width: `${width}%` }} />
          ))}
        </motion.div>
      </div>
    </div>
  );
}
