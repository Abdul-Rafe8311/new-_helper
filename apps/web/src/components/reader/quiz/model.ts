import type { Edition } from "@/lib/api";

/** One multiple-choice question as the composer wrote it into `edition.layout.quiz`. */
export type QuizQuestion = {
  question: string;
  options: string[];
  /** Index into `options` of the right answer. */
  answer: number;
  /** One line, from the article, on why the answer is right (older editions have none). */
  explanation: string | null;
  /** The story this answer is logged against. */
  itemId: string;
};

export type Recall = {
  /** The day of the paper the question came from (yesterday's). */
  date: string;
  question: QuizQuestion;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function questionFrom(raw: unknown, fallbackItemId: string | null): QuizQuestion | null {
  if (!isRecord(raw)) return null;
  const { question, options, answer, explanation, item_id: itemId } = raw;
  if (typeof question !== "string" || !question.trim()) return null;
  if (!Array.isArray(options) || options.length < 2 || !options.every((o) => typeof o === "string")) return null;
  if (typeof answer !== "number" || !Number.isInteger(answer) || answer < 0 || answer >= options.length) return null;
  const item = typeof itemId === "string" && itemId ? itemId : fallbackItemId;
  if (!item) return null; // an answer cannot be logged without a story to hang it on
  return {
    question: question.trim(),
    options: options as string[],
    answer,
    explanation: typeof explanation === "string" && explanation.trim() ? explanation.trim() : null,
    itemId: item,
  };
}

/**
 * The edition's questions, skipping any that are malformed. Older editions, and papers whose
 * composer produced none, give an empty list, which is what hides the quiz.
 */
export function questionsOf(edition: Pick<Edition, "layout" | "items"> | null | undefined): QuizQuestion[] {
  const layout: unknown = edition?.layout;
  if (!isRecord(layout) || !Array.isArray(layout.quiz)) return [];
  // Older questions name no story: file them under the lead (or, failing that, the first) story.
  const fallback =
    (typeof layout.lead_item_id === "string" ? layout.lead_item_id : null) ?? edition?.items[0]?.id ?? null;
  return layout.quiz.flatMap((raw) => questionFrom(raw, fallback) ?? []);
}

export type Verdict = { correct: boolean; explanation: string };

/** Score one pick. The explanation falls back to naming the right answer. */
export function scoreAnswer(question: QuizQuestion, choice: number): Verdict {
  const correct = choice === question.answer;
  const right = question.options[question.answer] ?? "";
  return { correct, explanation: question.explanation ?? `The answer is “${right}”.` };
}

/** The value logged in the `quiz_answer` event: 1 for right, 0 for wrong. */
export const answerValue = (verdict: Verdict): 1 | 0 => (verdict.correct ? 1 : 0);

/** The calendar day before `date` (YYYY-MM-DD); date maths in UTC so time zones cannot shift it. */
export function previousDay(date: string): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - 1);
  return day.toISOString().slice(0, 10);
}

/**
 * One question from yesterday's paper for today's "Still remember?" card. `yesterday` must be
 * the edition for the day before `todayDate`; anything else (a missing paper, the wrong day,
 * today's own edition) gives nothing. The pick is stable for a day so a refresh shows the same one.
 */
export function recallFrom(todayDate: string, yesterday: Edition | null): Recall | null {
  if (!yesterday || yesterday.status !== "ready" || yesterday.date !== previousDay(todayDate)) return null;
  const questions = questionsOf(yesterday);
  if (questions.length === 0) return null;
  const dayNumber = Math.floor(Date.parse(`${todayDate}T00:00:00Z`) / 86_400_000);
  return { date: yesterday.date, question: questions[dayNumber % questions.length] };
}

/** The streak as the reader should see it once they have just finished today's quiz. */
export function streakAfterFinishing(streak: number, doneToday: boolean): number {
  return doneToday ? streak : streak + 1;
}
