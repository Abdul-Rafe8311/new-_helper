import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EditionItem } from "@/lib/api";

import { ChromeProvider } from "../chrome-context";
import { stateFor, type ItemStates } from "../model";
import { useReaderCore } from "../use-reader-core";

const track = vi.hoisted(() => vi.fn());
vi.mock("@/lib/tracking-client", () => ({ tracker: { track } }));

function item(n: number): EditionItem {
  return {
    id: `item-${n}`,
    article_id: `article-${n}`,
    section: "Tech",
    position: n,
    slot: "standard",
    headline: `Headline ${n}`,
    summary: "",
    key_facts: [],
    why_text: null,
    url: `https://example.com/${n}`,
    source: "The Wire",
    image_url: null,
    published_at: null,
    score: null,
    score_breakdown: {},
    state: { read: false, saved: false, skipped: false, reaction: null },
  };
}

const ITEMS = [item(1), item(2), item(3)];
const selectAll = (states: ItemStates) => ITEMS.filter((i) => !stateFor(states, i).skipped);

function Harness() {
  const core = useReaderCore(selectAll);
  return (
    <div>
      <ul>
        {core.items.map((i) => (
          <li key={i.id} id={`story-${i.id}`} data-story={i.id}>
            <a href="#" data-story-link>
              {i.headline}
            </a>
            {stateFor(core.states, i).read ? "(read)" : ""}
            {stateFor(core.states, i).saved ? "(saved)" : ""}
            {stateFor(core.states, i).reaction ?? ""}
          </li>
        ))}
      </ul>
      <p data-testid="focused">{core.focusedId ?? "none"}</p>
      {core.toast.toast ? (
        <div role="status">
          {core.toast.toast.message}
          {core.toast.toast.undo ? <button onClick={core.toast.toast.undo}>Undo</button> : null}
        </div>
      ) : null}
      <input aria-label="search" />
    </div>
  );
}

const renderHarness = () =>
  render(
    <ChromeProvider>
      <Harness />
    </ChromeProvider>,
  );

const press = (key: string, init: KeyboardEventInit = {}) =>
  act(() => {
    fireEvent.keyDown(window, { key, ...init });
  });

const events = () => track.mock.calls.map(([event]) => event);

beforeEach(() => {
  track.mockClear();
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as never;
});

describe("useReaderCore keyboard shortcuts", () => {
  it("j and k move focus through the visible stories, onto the story link, and stop at the ends", () => {
    renderHarness();
    press("j");
    expect(screen.getByTestId("focused")).toHaveTextContent("item-1");
    expect(screen.getByRole("link", { name: "Headline 1" })).toHaveFocus();
    press("j");
    press("j");
    press("j");
    expect(screen.getByTestId("focused")).toHaveTextContent("item-3");
    press("k");
    expect(screen.getByTestId("focused")).toHaveTextContent("item-2");
  });

  it("s toggles save on the focused story and logs it (1 on, 0 to retract)", () => {
    renderHarness();
    press("j");
    press("s");
    expect(screen.getByText(/Headline 1/).closest("li")).toHaveTextContent("(saved)");
    press("s");
    expect(events().filter((e) => e.type === "save").map((e) => e.value)).toEqual([1, 0]);
  });

  it("m and l set a reaction; switching retracts the other; pressing again clears", () => {
    renderHarness();
    press("j");
    press("m");
    press("l");
    expect(events().map((e) => [e.type, e.value])).toEqual([
      ["more_like", 1],
      ["more_like", 0],
      ["less_like", 1],
    ]);
    expect(screen.getByText(/Headline 1/).closest("li")).toHaveTextContent("less");
    press("l");
    expect(screen.getByText(/Headline 1/).closest("li")).not.toHaveTextContent("less");
  });

  it("x skips the story, moves focus on, and Undo brings it back", () => {
    renderHarness();
    press("j");
    press("x");
    expect(screen.queryByText(/Headline 1/)).not.toBeInTheDocument();
    expect(screen.getByTestId("focused")).toHaveTextContent("item-2");
    expect(screen.getByRole("status")).toHaveTextContent("Story skipped");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(screen.getByText(/Headline 1/)).toBeInTheDocument();
    expect(events().filter((e) => e.type === "skip").map((e) => e.value)).toEqual([1, 0]);
  });

  it("Shift+A marks everything shown as read, once", () => {
    renderHarness();
    press("A", { shiftKey: true });
    expect(screen.getAllByText(/\(read\)/)).toHaveLength(3);
    expect(events().filter((e) => e.type === "mark_read")).toHaveLength(3);
    press("A", { shiftKey: true });
    expect(events().filter((e) => e.type === "mark_read")).toHaveLength(3);
  });

  it("o opens the original through the logging redirect in a new tab", () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    renderHarness();
    press("j");
    press("o");
    expect(open).toHaveBeenCalledWith("/api/r/item-1", "_blank", "noopener");
    expect(screen.getByText(/Headline 1/).closest("li")).toHaveTextContent("(read)");
    // the redirect logs the open itself, so no separate event is sent
    expect(events()).toEqual([]);
  });

  it("does nothing while typing in a field or with a modifier held", () => {
    renderHarness();
    const input = screen.getByLabelText("search");
    input.focus();
    act(() => {
      fireEvent.keyDown(input, { key: "j" });
    });
    press("j", { metaKey: true });
    expect(screen.getByTestId("focused")).toHaveTextContent("none");
  });

  it("does nothing on s, m, l, x, o before a story is focused", () => {
    renderHarness();
    for (const key of ["s", "m", "l", "x", "o"]) press(key);
    expect(events()).toEqual([]);
  });
});
