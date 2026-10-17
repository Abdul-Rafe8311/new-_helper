import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  Attention,
  FLUSH_INTERVAL_MS,
  MAX_BATCH,
  Tracker,
  URGENT_FLUSH_MS,
  type SendResult,
  type TrackedEvent,
} from "../tracking";

const event = (n: number, type: TrackedEvent["type"] = "impression"): TrackedEvent => ({
  type,
  edition_item_id: `item-${n}`,
});

function setup(result: SendResult = "ok") {
  const sent: TrackedEvent[][] = [];
  const beacons: TrackedEvent[][] = [];
  const send = vi.fn(async (batch: TrackedEvent[]) => {
    sent.push(batch);
    return result;
  });
  const beacon = vi.fn((batch: TrackedEvent[]) => {
    beacons.push(batch);
    return true;
  });
  return { tracker: new Tracker({ send, beacon }), send, beacon, sent, beacons };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("Tracker", () => {
  it("sends nothing until the interval, then everything in one batch", async () => {
    const { tracker, sent } = setup();
    tracker.start();
    tracker.track(event(1));
    tracker.track(event(2));
    await vi.advanceTimersByTimeAsync(FLUSH_INTERVAL_MS - 1);
    expect(sent).toEqual([]);
    await vi.advanceTimersByTimeAsync(1);
    expect(sent).toEqual([[event(1), event(2)]]);
    expect(tracker.pending).toBe(0);
    tracker.stop();
  });

  it("does not call the API for an empty queue", async () => {
    const { tracker, send } = setup();
    tracker.start();
    await vi.advanceTimersByTimeAsync(FLUSH_INTERVAL_MS * 3);
    expect(send).not.toHaveBeenCalled();
    tracker.stop();
  });

  it("flushes soon after a deliberate action", async () => {
    const { tracker, sent } = setup();
    tracker.track(event(1, "save"), { urgent: true });
    tracker.track(event(2, "impression"));
    await vi.advanceTimersByTimeAsync(URGENT_FLUSH_MS);
    expect(sent).toEqual([[event(1, "save"), event(2)]]);
  });

  it("splits large queues into batches of at most 100", async () => {
    const { tracker, sent } = setup();
    for (let n = 0; n < 250; n++) tracker.track(event(n));
    await tracker.flush();
    expect(sent.map((b) => b.length)).toEqual([MAX_BATCH, MAX_BATCH, 50]);
  });

  it("keeps events that failed to send and retries them with the next ones", async () => {
    const { tracker, send, sent } = setup("retry");
    tracker.track(event(1));
    await tracker.flush();
    expect(tracker.pending).toBe(1);
    send.mockImplementation(async (batch) => {
      sent.push(batch);
      return "ok";
    });
    tracker.track(event(2));
    await tracker.flush();
    expect(sent.at(-1)).toEqual([event(1), event(2)]);
    expect(tracker.pending).toBe(0);
  });

  it("drops events the server refused outright", async () => {
    const { tracker } = setup("drop");
    tracker.track(event(1));
    await tracker.flush();
    expect(tracker.pending).toBe(0);
  });

  it("treats a thrown send as a retry", async () => {
    const { tracker, send } = setup();
    send.mockRejectedValueOnce(new Error("offline"));
    tracker.track(event(1));
    await tracker.flush();
    expect(tracker.pending).toBe(1);
  });

  it("hands the queue to sendBeacon when the tab is hidden", () => {
    const { tracker, beacons, send } = setup();
    tracker.track(event(1));
    tracker.track(event(2));
    tracker.flushWithBeacon();
    expect(beacons).toEqual([[event(1), event(2)]]);
    expect(send).not.toHaveBeenCalled();
    expect(tracker.pending).toBe(0);
  });

  it("keeps the queue if the browser refuses the beacon", () => {
    const { tracker, beacon } = setup();
    beacon.mockReturnValue(false);
    tracker.track(event(1));
    tracker.flushWithBeacon();
    expect(tracker.pending).toBe(1);
  });

  it("caps the queue so a long offline spell cannot grow it without bound", () => {
    const { tracker } = setup();
    for (let n = 0; n < 700; n++) tracker.track(event(n));
    expect(tracker.pending).toBeLessThanOrEqual(500);
  });
});

describe("Attention", () => {
  function watch() {
    const { tracker } = setup();
    const tracked = vi.spyOn(tracker, "track");
    return { attention: new Attention(tracker), tracked };
  }

  it("logs an impression after one second at >= 50% visible, once", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(999);
    expect(tracked).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(tracked).toHaveBeenCalledWith({ type: "impression", edition_item_id: "a" });

    attention.setIntersecting("a", false);
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(5000);
    expect(tracked.mock.calls.filter(([e]) => e.type === "impression")).toHaveLength(1);
  });

  it("logs no impression for a card scrolled past quickly", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(600);
    attention.setIntersecting("a", false);
    vi.advanceTimersByTime(5000);
    expect(tracked).not.toHaveBeenCalled();
  });

  it("logs dwell seconds when the card leaves view", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(4200);
    attention.setIntersecting("a", false);
    expect(tracked).toHaveBeenLastCalledWith({ type: "dwell", edition_item_id: "a", value: 4.2 });
  });

  it("adds up separate looks as separate dwell events", () => {
    const { attention, tracked } = watch();
    for (let i = 0; i < 2; i++) {
      attention.setIntersecting("a", true);
      vi.advanceTimersByTime(2000);
      attention.setIntersecting("a", false);
      vi.advanceTimersByTime(3000);
    }
    expect(tracked.mock.calls.filter(([e]) => e.type === "dwell")).toHaveLength(2);
  });

  it("stops the clock while the tab is in the background", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(3000);
    attention.setDocumentVisible(false);
    expect(tracked).toHaveBeenLastCalledWith({ type: "dwell", edition_item_id: "a", value: 3 });
    vi.advanceTimersByTime(60_000);
    attention.setDocumentVisible(true);
    vi.advanceTimersByTime(1500);
    attention.setIntersecting("a", false);
    expect(tracked).toHaveBeenLastCalledWith({ type: "dwell", edition_item_id: "a", value: 1.5 });
  });

  it("closes out dwell when a card is removed from the page", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    vi.advanceTimersByTime(2000);
    attention.release("a");
    expect(tracked).toHaveBeenLastCalledWith({ type: "dwell", edition_item_id: "a", value: 2 });
  });

  it("tracks cards independently", () => {
    const { attention, tracked } = watch();
    attention.setIntersecting("a", true);
    attention.setIntersecting("b", true);
    vi.advanceTimersByTime(1000);
    expect(tracked.mock.calls.map(([e]) => e.edition_item_id).sort()).toEqual(["a", "b"]);
  });
});
