"use client";

import { Check, X } from "lucide-react";
import { useId, useState } from "react";

import { tracker } from "@/lib/tracking-client";
import { cn } from "@/lib/utils";

import { answerValue, scoreAnswer, type QuizQuestion, type Verdict } from "./model";

export type AnswerKind = "quiz" | "recall";

type Props = {
  question: QuizQuestion;
  /** Position within its quiz; logged so a day's answers can be told apart. */
  index: number;
  kind: AnswerKind;
  onAnswered?: (verdict: Verdict) => void;
  /** Lay the options out in a single row on wide screens (the compact "Still remember?" card). */
  compact?: boolean;
};

const LETTERS = "ABCD";

/** Record the answer against its story: the same event shape the story cards use. */
function logAnswer(question: QuizQuestion, index: number, kind: AnswerKind, verdict: Verdict): void {
  tracker.track(
    { type: "quiz_answer", edition_item_id: question.itemId, value: answerValue(verdict), meta: { q: index, kind } },
    { urgent: true },
  );
}

/**
 * One question with instant feedback. Options are real buttons; the verdict and the one-line
 * explanation sit in a polite live region so a screen reader announces them after the pick.
 */
export function QuestionCard({ question, index, kind, onAnswered, compact = false }: Props) {
  const id = useId();
  const [choice, setChoice] = useState<number | null>(null);
  const verdict = choice === null ? null : scoreAnswer(question, choice);

  function pick(option: number) {
    if (choice !== null) return;
    const result = scoreAnswer(question, option);
    setChoice(option);
    logAnswer(question, index, kind, result);
    onAnswered?.(result);
  }

  return (
    <div data-testid={`${kind}-question`} role="group" aria-labelledby={`${id}-q`}>
      <p id={`${id}-q`} className="font-sans text-[17px] leading-snug font-bold text-balance sm:text-lg">
        {question.question}
      </p>
      <div className={cn("mt-3 grid gap-2 sm:grid-cols-2", compact && question.options.length === 3 && "lg:grid-cols-3")}>
        {question.options.map((option, i) => {
          const chosen = choice === i;
          const right = choice !== null && i === question.answer;
          return (
            <button
              key={option}
              type="button"
              disabled={choice !== null && !chosen && !right}
              aria-disabled={choice !== null}
              data-state={right ? "correct" : chosen ? "wrong" : "idle"}
              onClick={() => pick(i)}
              className={cn(
                "flex min-h-11 items-start gap-3 rounded-xl border px-3.5 py-2.5 text-left font-sans text-[15px] leading-snug transition-colors outline-none",
                "focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-ring",
                choice === null && "border-rule bg-canvas hover:border-cat hover:bg-paper-2",
                right && "border-emerald-600 bg-emerald-600/10 font-semibold",
                chosen && !right && "border-rose-600 bg-rose-600/10 font-semibold",
                choice !== null && !right && !chosen && "border-rule opacity-60",
              )}
            >
              <span
                aria-hidden="true"
                className="mt-px flex size-6 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold"
              >
                {right ? <Check className="size-3.5" /> : chosen ? <X className="size-3.5" /> : LETTERS[i]}
              </span>
              <span>{option}</span>
            </button>
          );
        })}
      </div>
      <p role="status" aria-live="polite" data-testid="quiz-feedback" className="mt-2.5 min-h-6 font-serif text-[15px] leading-snug">
        {verdict ? (
          <>
            <strong className={cn("font-sans font-bold", verdict.correct ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400")}>
              {verdict.correct ? "Correct." : "Not quite."}
            </strong>{" "}
            <span className="text-muted">{verdict.explanation}</span>
          </>
        ) : null}
      </p>
    </div>
  );
}
