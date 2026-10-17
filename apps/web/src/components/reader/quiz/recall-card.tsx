"use client";

import { QuestionCard } from "./question-card";
import type { Recall } from "./model";

/** "Still remember?": one question from yesterday's paper, answered the same way as the quiz. */
export function RecallCard({ recall }: { recall: Recall }) {
  return (
    <section
      aria-labelledby="recall-title"
      data-testid="recall"
      className="mx-auto mb-8 w-full max-w-3xl rounded-[14px] border border-rule bg-surface p-5 shadow-sm"
    >
      <h2 id="recall-title" className="font-sans text-xs font-bold tracking-[0.14em] text-cat uppercase">
        Still remember? <span className="font-medium text-muted normal-case tracking-normal">From yesterday&rsquo;s paper</span>
      </h2>
      <div className="mt-3">
        <QuestionCard question={recall.question} index={0} kind="recall" />
      </div>
    </section>
  );
}
