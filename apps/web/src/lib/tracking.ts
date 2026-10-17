/**
 * Reader tracking: what was seen, for how long, and what the reader did with it.
 *
 * `Tracker` batches events and ships them to POST /api/events every 10s, sooner after a
 * deliberate action, and with `sendBeacon` when the tab is hidden. `Attention` turns "this
 * card is on screen" signals into impressions (>= 50% visible for >= 1s) and dwell time.
 * Both are plain classes with injected I/O so they can be tested without a browser.
 */

export type EventType =
  | "impression"
  | "dwell"
  | "skip"
  | "more_like"
  | "less_like"
  | "save"
  | "mark_read"
  | "quiz_answer";

export type TrackedEvent = {
  type: EventType;
  edition_item_id: string;
  /** Seconds for `dwell`; for the toggles, `0` retracts an earlier event. */
  value?: number;
  meta?: Record<string, string | number | boolean | null>;
};

export const FLUSH_INTERVAL_MS = 10_000;
/** After a deliberate action (skip, save, ...) flush soon, so the next page sees it. */
export const URGENT_FLUSH_MS = 400;
export const MAX_BATCH = 100;
const MAX_QUEUE = 500;

export const IMPRESSION_RATIO = 0.5;
export const IMPRESSION_MS = 1000;
/** Shorter looks than this are scrolling past, not reading. */
export const MIN_DWELL_MS = 1000;

export type SendResult = "ok" | "retry" | "drop";

export type TrackerOptions = {
  /** Deliver a batch; "retry" puts it back in the queue, "drop" discards it (e.g. a 4xx). */
  send: (events: TrackedEvent[]) => Promise<SendResult>;
  /** Fire-and-forget delivery that survives the page closing; false if the browser refused. */
  beacon: (events: TrackedEvent[]) => boolean;
  intervalMs?: number;
};

export class Tracker {
  private queue: TrackedEvent[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private urgent: ReturnType<typeof setTimeout> | null = null;
  private inFlight: Promise<void> = Promise.resolve();

  constructor(private readonly options: TrackerOptions) {}

  get pending(): number {
    return this.queue.length;
  }

  track(event: TrackedEvent, { urgent = false }: { urgent?: boolean } = {}): void {
    this.queue.push(event);
    if (this.queue.length > MAX_QUEUE) this.queue.splice(0, this.queue.length - MAX_QUEUE);
    if (this.queue.length >= MAX_BATCH) {
      void this.flush();
    } else if (urgent && this.urgent === null) {
      this.urgent = setTimeout(() => {
        this.urgent = null;
        void this.flush();
      }, URGENT_FLUSH_MS);
    }
  }

  /** Send everything queued, in batches of at most 100. Calls are serialised. */
  flush(): Promise<void> {
    this.inFlight = this.inFlight.then(() => this.drain());
    return this.inFlight;
  }

  private async drain(): Promise<void> {
    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, MAX_BATCH);
      let result: SendResult;
      try {
        result = await this.options.send(batch);
      } catch {
        result = "retry";
      }
      if (result === "retry") {
        this.queue.unshift(...batch);
        if (this.queue.length > MAX_QUEUE) this.queue.length = MAX_QUEUE;
        return; // try again on the next tick, not in a tight loop
      }
    }
  }

  /** For `visibilitychange: hidden` / `pagehide`: hand the queue to sendBeacon. */
  flushWithBeacon(): void {
    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, MAX_BATCH);
      if (!this.options.beacon(batch)) {
        this.queue.unshift(...batch);
        return;
      }
    }
  }

  start(): () => void {
    this.timer ??= setInterval(() => void this.flush(), this.options.intervalMs ?? FLUSH_INTERVAL_MS);
    return () => this.stop();
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    if (this.urgent) clearTimeout(this.urgent);
    this.timer = null;
    this.urgent = null;
  }
}

type Watch = {
  intersecting: boolean;
  /** When the card became (and stayed) visible, or null. */
  since: number | null;
  impression: ReturnType<typeof setTimeout> | null;
  impressed: boolean;
};

/**
 * Per-card attention. A card counts as visible while it is >= 50% on screen *and* the tab is in
 * the foreground. After 1s of that it logs one impression; every time it leaves view it logs the
 * time it was seen as a `dwell` event (if at least a second).
 */
export class Attention {
  private watches = new Map<string, Watch>();
  private documentVisible = true;

  constructor(
    private readonly tracker: Tracker,
    private readonly now: () => number = Date.now,
  ) {}

  setIntersecting(itemId: string, intersecting: boolean): void {
    const watch = this.watch(itemId);
    watch.intersecting = intersecting;
    this.update(itemId, watch);
  }

  setDocumentVisible(visible: boolean): void {
    this.documentVisible = visible;
    for (const [itemId, watch] of this.watches) this.update(itemId, watch);
  }

  /** The card left the page: close out its dwell and forget it. */
  release(itemId: string): void {
    const watch = this.watches.get(itemId);
    if (!watch) return;
    watch.intersecting = false;
    this.update(itemId, watch);
    this.watches.delete(itemId);
  }

  private watch(itemId: string): Watch {
    let watch = this.watches.get(itemId);
    if (!watch) {
      watch = { intersecting: false, since: null, impression: null, impressed: false };
      this.watches.set(itemId, watch);
    }
    return watch;
  }

  private update(itemId: string, watch: Watch): void {
    const visible = watch.intersecting && this.documentVisible;
    if (visible && watch.since === null) {
      watch.since = this.now();
      if (!watch.impressed) {
        watch.impression = setTimeout(() => {
          watch.impression = null;
          watch.impressed = true;
          this.tracker.track({ type: "impression", edition_item_id: itemId });
        }, IMPRESSION_MS);
      }
    } else if (!visible && watch.since !== null) {
      const seen = this.now() - watch.since;
      watch.since = null;
      if (watch.impression) clearTimeout(watch.impression);
      watch.impression = null;
      if (seen >= MIN_DWELL_MS) {
        this.tracker.track({ type: "dwell", edition_item_id: itemId, value: Math.round(seen / 100) / 10 });
      }
    }
  }
}
