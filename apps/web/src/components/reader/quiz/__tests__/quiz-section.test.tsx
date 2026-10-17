import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuizSection } from "../quiz-section";
import { RecallCard } from "../recall-card";
import type { QuizQuestion } from "../model";

const track = vi.hoisted(() => vi.fn());
const quizStreak = vi.hoisted(() => vi.fn());

vi.mock("@/lib/tracking-client", () => ({ tracker: { track } }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { quizStreak },
}));

const question = (n: number): QuizQuestion => ({
  question: `Question ${n}?`,
  options: ["Right", "Wrong", "Also wrong"],
  answer: 0,
  explanation: `Because of story ${n}.`,
  itemId: `item-${n}`,
});
const THREE = [1, 2, 3].map(question);

beforeEach(() => {
  track.mockReset();
  quizStreak.mockReset();
  quizStreak.mockResolvedValue({ streak: 0, done_today: false });
});

describe("QuizSection", () => {
  it("renders nothing without questions", () => {
    const { container } = render(<QuizSection questions={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("gives instant feedback and logs 1 for a right answer, 0 for a wrong one", () => {
    render(<QuizSection questions={THREE} />);
    const groups = screen.getAllByRole("group");
    fireEvent.click(within(groups[0]).getByRole("button", { name: /Right/ }));
    fireEvent.click(within(groups[1]).getByRole("button", { name: /Wrong$/ }));

    expect(within(groups[0]).getByRole("status")).toHaveTextContent("Correct. Because of story 1.");
    expect(within(groups[1]).getByRole("status")).toHaveTextContent("Not quite. Because of story 2.");
    expect(track).toHaveBeenNthCalledWith(
      1,
      { type: "quiz_answer", edition_item_id: "item-1", value: 1, meta: { q: 0, kind: "quiz" } },
      { urgent: true },
    );
    expect(track).toHaveBeenNthCalledWith(
      2,
      { type: "quiz_answer", edition_item_id: "item-2", value: 0, meta: { q: 1, kind: "quiz" } },
      { urgent: true },
    );
  });

  it("logs a question once and ignores a second tap", () => {
    render(<QuizSection questions={THREE} />);
    const [first] = screen.getAllByRole("group");
    fireEvent.click(within(first).getByRole("button", { name: /Right/ }));
    fireEvent.click(within(first).getByRole("button", { name: /Right/ }));
    expect(track).toHaveBeenCalledTimes(1);
  });

  it("shows the streak, and counts today once all questions are answered", async () => {
    quizStreak.mockResolvedValue({ streak: 2, done_today: false });
    render(<QuizSection questions={THREE} />);
    await waitFor(() => expect(screen.getByTestId("quiz-streak-count")).toHaveTextContent("2"));
    for (const group of screen.getAllByRole("group")) fireEvent.click(within(group).getByRole("button", { name: /Right/ }));
    expect(screen.getByTestId("quiz-streak-count")).toHaveTextContent("3");
    expect(screen.getByText("You got 3 of 3.")).toBeInTheDocument();
  });

  it("does not add today twice when the server already counted it", async () => {
    quizStreak.mockResolvedValue({ streak: 5, done_today: true });
    render(<QuizSection questions={[question(1)]} />);
    await waitFor(() => expect(screen.getByTestId("quiz-streak-count")).toHaveTextContent("5"));
    fireEvent.click(screen.getByRole("button", { name: /Right/ }));
    expect(screen.getByTestId("quiz-streak-count")).toHaveTextContent("5");
  });
});

describe("RecallCard", () => {
  it("answers with the same feedback and logs a recall answer", () => {
    render(<RecallCard recall={{ date: "2026-10-16", question: question(9) }} />);
    expect(screen.getByRole("heading", { name: /Still remember/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Wrong$/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Not quite. Because of story 9.");
    expect(track).toHaveBeenCalledWith(
      { type: "quiz_answer", edition_item_id: "item-9", value: 0, meta: { q: 0, kind: "recall" } },
      { urgent: true },
    );
    expect(quizStreak).not.toHaveBeenCalled();
  });
});
