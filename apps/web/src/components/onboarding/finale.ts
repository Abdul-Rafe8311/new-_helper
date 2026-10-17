/** The finale's stage copy and the pure rules for turning an edition status into a phase. */
import type { EditionStatus } from "@/lib/api";

export const PRESS_STAGES = [
  { key: "gathering", label: "Gathering", message: "Gathering today's stories from across the web…" },
  { key: "choosing", label: "Choosing", message: "Choosing what matters to you…" },
  { key: "writing", label: "Writing", message: "Writing your summaries…" },
  { key: "typesetting", label: "Typesetting", message: "Typesetting your front page…" },
] as const;

export type PressStage = (typeof PRESS_STAGES)[number]["key"];

export type Phase =
  | { kind: "starting" }
  | { kind: "printing"; stage: PressStage }
  | { kind: "ready" }
  | { kind: "failed"; message: string };

export const POLL_MS = 1200;
export const GIVE_UP_MS = 120_000;

export function stageIndex(stage: PressStage): number {
  return PRESS_STAGES.findIndex((s) => s.key === stage);
}

/** Never let the animation step backwards if a poll returns an older stage. */
export function phaseFromStatus(status: EditionStatus, previous: Phase): Phase {
  if (status.status === "ready") return { kind: "ready" };
  if (status.status === "failed") {
    return { kind: "failed", message: "We couldn't print your first edition." };
  }
  const reported = PRESS_STAGES.find((s) => s.key === status.stage)?.key ?? "gathering";
  const before = previous.kind === "printing" ? stageIndex(previous.stage) : 0;
  const stage = stageIndex(reported) >= before ? reported : PRESS_STAGES[before].key;
  return { kind: "printing", stage };
}
