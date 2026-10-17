import { describe, expect, it } from "vitest";

import type { Edition } from "@/lib/api";
import { quizEnabled } from "@/lib/config";

import {
  answerValue,
  previousDay,
  questionsOf,
  recallFrom,
  scoreAnswer,
  streakAfterFinishing,
  type QuizQuestion,
} from "../model";

const QUESTION = { question: "Who signed?", options: ["Agents", "Banks", "Babar"], answer: 0, item_id: "item-1" };

function edition(date: string, quiz: unknown[] | undefined, over: Partial<Edition> = {}): Edition {
  return {
    id: `ed-${date}`,
    date,
    number: 1,
    status: "ready",
    title: "Paper",
    editor_note: null,
    layout: { lead_item_id: "lead-1", ...(quiz ? { quiz } : {}) },
    items: [],
    stats: {},
    generated_at: null,
    ...over,
  } as Edition;
}

const asked = (explanation: string | null = "Agents signed their own contracts."): QuizQuestion => ({
  question: "Who signed?",
  options: ["Agents", "Banks", "Babar"],
  answer: 0,
  explanation,
  itemId: "item-1",
});

describe("scoring", () => {
  it("marks the right option correct and logs 1", () => {
    const verdict = scoreAnswer(asked(), 0);
    expect(verdict.correct).toBe(true);
    expect(answerValue(verdict)).toBe(1);
  });

  it("marks any other option wrong and logs 0", () => {
    const verdict = scoreAnswer(asked(), 2);
    expect(verdict.correct).toBe(false);
    expect(answerValue(verdict)).toBe(0);
  });

  it("explains with the article's line, or names the answer when there is none", () => {
    expect(scoreAnswer(asked(), 1).explanation).toBe("Agents signed their own contracts.");
    expect(scoreAnswer(asked(null), 1).explanation).toBe("The answer is “Agents”.");
  });
});

describe("questionsOf", () => {
  it("reads the composer's questions", () => {
    const [q] = questionsOf(edition("2026-10-17", [{ ...QUESTION, explanation: " Because. " }]));
    expect(q).toEqual({ ...asked("Because."), explanation: "Because." });
  });

  it("is empty when there is no quiz, so the section is hidden", () => {
    expect(questionsOf(edition("2026-10-17", undefined))).toEqual([]);
    expect(questionsOf(edition("2026-10-17", []))).toEqual([]);
    expect(questionsOf(null)).toEqual([]);
  });

  it("skips malformed questions", () => {
    const bad = [{ question: "", options: ["a", "b"], answer: 0 }, { ...QUESTION, answer: 9 }, { ...QUESTION, options: ["only"] }, "x"];
    expect(questionsOf(edition("2026-10-17", [...bad, QUESTION]))).toHaveLength(1);
  });

  it("files an older question without a story under the lead story", () => {
    const { item_id: _unused, ...legacy } = QUESTION;
    expect(questionsOf(edition("2026-10-17", [legacy]))[0].itemId).toBe("lead-1");
  });
});

describe("Still remember?", () => {
  const today = "2026-10-17";

  it("uses yesterday's edition", () => {
    const recall = recallFrom(today, edition("2026-10-16", [QUESTION]));
    expect(recall?.date).toBe("2026-10-16");
    expect(recall?.question.question).toBe("Who signed?");
  });

  it("never uses today's own edition or any other day", () => {
    expect(recallFrom(today, edition(today, [QUESTION]))).toBeNull();
    expect(recallFrom(today, edition("2026-10-15", [QUESTION]))).toBeNull();
  });

  it("is absent without a paper, a finished paper or any questions", () => {
    expect(recallFrom(today, null)).toBeNull();
    expect(recallFrom(today, edition("2026-10-16", [QUESTION], { status: "pending" }))).toBeNull();
    expect(recallFrom(today, edition("2026-10-16", undefined))).toBeNull();
  });

  it("shows the same question all day", () => {
    const paper = edition("2026-10-16", [QUESTION, { ...QUESTION, question: "Second?" }, { ...QUESTION, question: "Third?" }]);
    expect(recallFrom(today, paper)?.question).toEqual(recallFrom(today, paper)?.question);
  });

  it("crosses month and year ends", () => {
    expect(previousDay("2026-03-01")).toBe("2026-02-28");
    expect(previousDay("2027-01-01")).toBe("2026-12-31");
  });
});

describe("streak shown after finishing", () => {
  it("adds today once, and not again if today already counted", () => {
    expect(streakAfterFinishing(0, false)).toBe(1);
    expect(streakAfterFinishing(4, false)).toBe(5);
    expect(streakAfterFinishing(5, true)).toBe(5);
  });
});

describe("QUIZ_ENABLED", () => {
  it("defaults to on and turns off only when told", () => {
    expect(quizEnabled({})).toBe(true);
    expect(quizEnabled({ QUIZ_ENABLED: "" })).toBe(true);
    expect(quizEnabled({ QUIZ_ENABLED: "true" })).toBe(true);
    expect(quizEnabled({ QUIZ_ENABLED: "false" })).toBe(false);
    expect(quizEnabled({ QUIZ_ENABLED: "0" })).toBe(false);
  });
});
