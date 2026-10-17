"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** The current year, read on the client so the statically built page never goes stale. */
export function CurrentYear() {
  const year = useSyncExternalStore(
    subscribe,
    () => String(new Date().getFullYear()),
    () => "",
  );
  return <span suppressHydrationWarning>{year}</span>;
}
