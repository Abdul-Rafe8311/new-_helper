"use client";

import { Flame } from "lucide-react";
import { useState } from "react";

import type { Verdict, QuizQuestion } from "./model";
import { streakAfterFinishing } from "./model";
import { QuestionCard } from "./question-card";
import { useQuizStreak } from "./use-quiz-streak";

/**
 * The end-of-paper recall quiz. The header carries the streak: consecutive days the reader
 * answered every question. Finishing today bumps it at once; the server count catches up as the
 * answers are delivered. Renders nothing when the edition has no questions.
 */
export function QuizSection({ questions }: { questions: QuizQuestion[] }) {
  const server = useQuizStreak();
  const [results, setResults] = useState<Record<number, Verdict>>({});
  if (questions.length === 0) return null;

  const answered = Object.keys(results).length;
  const finished = answered === questions.length;
  const correct = Object.values(results).filter((r) => r.correct).length;
  const streak = server ? (finished ? streakAfterFinishing(server.streak, server.done_today) : server.streak) : null;

  return (
    <section aria-labelledby="quiz-title" data-testid="quiz" className="mt-14 w-full max-w-3xl">
      <div className="rounded-[14px] border border-rule bg-surface p-5 shadow-sm sm:p-7">
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-rule pb-4">
          <div>
            <h2 id="quiz-title" className="font-display text-2xl font-black tracking-tight sm:text-3xl">
              Can you name three things you learned?
            </h2>
            <p className="mt-1 font-sans text-sm text-muted">
              {finished ? `You got ${correct} of ${questions.length}.` : `${answered} of ${questions.length} answered`}
            </p>
          </div>
          {streak !== null ? (
            <p
              data-testid="quiz-streak"
              className="flex items-center gap-1.5 rounded-full border border-rule bg-canvas px-3 py-1.5 font-sans text-sm font-semibold"
            >
              <Flame aria-hidden="true" className="size-4 text-cat" />
              <span>
                Streak: <span data-testid="quiz-streak-count">{streak}</span> {streak === 1 ? "day" : "days"}
              </span>
            </p>
          ) : null}
        </header>
        <ol className="mt-5 space-y-7">
          {questions.map((question, index) => (
            <li key={`${index}-${question.question}`} className="flex gap-3">
              <span aria-hidden="true" className="w-5 shrink-0 font-display text-2xl leading-none font-black text-cat">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <QuestionCard
                  question={question}
                  index={index}
                  kind="quiz"
                  onAnswered={(verdict) => setResults((previous) => ({ ...previous, [index]: verdict }))}
                />
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
