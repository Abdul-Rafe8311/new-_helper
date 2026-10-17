"use client";

import { Tracker, type SendResult, type TrackedEvent } from "@/lib/tracking";

const ENDPOINT = "/api/events";

async function send(events: TrackedEvent[]): Promise<SendResult> {
  try {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      credentials: "same-origin",
      keepalive: true,
    });
    if (response.ok) return "ok";
    // 429 and 5xx are worth another try; a 4xx means the batch itself is wrong or we are signed out
    return response.status === 429 || response.status >= 500 ? "retry" : "drop";
  } catch {
    return "retry";
  }
}

function beacon(events: TrackedEvent[]): boolean {
  if (typeof navigator === "undefined" || typeof navigator.sendBeacon !== "function") return false;
  return navigator.sendBeacon(ENDPOINT, new Blob([JSON.stringify({ events })], { type: "application/json" }));
}

/** The one tracker for this tab. */
export const tracker = new Tracker({ send, beacon });
