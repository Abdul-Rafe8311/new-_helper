import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Edition } from "@/lib/api";

import { EditionPending, POLL_MS } from "../edition-pending";

const refresh = vi.hoisted(() => vi.fn());
const today = vi.hoisted(() => vi.fn());
const regenerate = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
vi.mock("../chrome-context", () => ({ useActiveEdition: () => undefined }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { editions: { today, regenerate } },
}));

const edition = (status: Edition["status"], stage?: string): Edition =>
  ({
    id: "e1",
    date: "2026-10-17",
    number: 1,
    status,
    title: null,
    editor_note: null,
    layout: {},
    items: [],
    stats: stage ? { stage } : {},
    generated_at: null,
  }) as Edition;

beforeEach(() => {
  vi.useFakeTimers();
  refresh.mockClear();
  today.mockReset();
  regenerate.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("EditionPending", () => {
  it("shows the press and the current stage while the paper is pending", () => {
    render(<EditionPending initial={edition("pending", "writing")} />);
    expect(screen.getByRole("heading", { name: "Your paper is on the press" })).toBeInTheDocument();
    expect(screen.getByTestId("printing-press")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Writing your headlines");
  });

  it("polls every 5 seconds and refreshes the page once the paper is ready", async () => {
    today.mockResolvedValueOnce(edition("pending", "choosing")).mockResolvedValueOnce(edition("ready"));
    render(<EditionPending initial={edition("pending", "gathering")} />);

    await act(() => vi.advanceTimersByTimeAsync(POLL_MS - 1));
    expect(today).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(today).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent("Choosing what matters to you");
    expect(refresh).not.toHaveBeenCalled();

    await act(() => vi.advanceTimersByTimeAsync(POLL_MS));
    expect(today).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("keeps polling through a failed request", async () => {
    today.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(edition("ready"));
    render(<EditionPending initial={edition("pending")} />);
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 2));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("offers to print when there is no paper, then starts polling", async () => {
    regenerate.mockResolvedValue(edition("pending", "gathering"));
    render(<EditionPending initial={null} />);
    expect(screen.getByRole("heading", { name: "No paper yet today" })).toBeInTheDocument();
    expect(today).not.toHaveBeenCalled();
    await act(async () => {
      screen.getByRole("button", { name: "Print today's paper" }).click();
    });
    expect(regenerate).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: "Your paper is on the press" })).toBeInTheDocument();
  });

  it("lets the reader try again after a failed build", () => {
    render(<EditionPending initial={edition("failed")} />);
    expect(screen.getByRole("heading", { name: "The press jammed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
