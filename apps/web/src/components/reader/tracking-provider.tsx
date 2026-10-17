"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { Attention } from "@/lib/tracking";
import { tracker } from "@/lib/tracking-client";

type Observe = (element: Element, itemId: string) => () => void;

const ObserveContext = createContext<Observe | null>(null);

/** A card counts as seen when half of it is on screen (or half the viewport, for tall cards). */
function seenEnough(entry: IntersectionObserverEntry): boolean {
  if (!entry.isIntersecting) return false;
  const viewport = entry.rootBounds?.height ?? window.innerHeight;
  return entry.intersectionRatio >= 0.5 || entry.intersectionRect.height >= viewport * 0.5;
}

const THRESHOLDS = Array.from({ length: 21 }, (_, i) => i / 20);

/**
 * Starts the event tracker for the signed-in area and watches story cards for impressions and
 * dwell time. Events go out every 10s and, via sendBeacon, when the tab is hidden.
 */
export function TrackingProvider({ children }: { children: ReactNode }) {
  const [attention] = useState(() => new Attention(tracker));
  const observer = useRef<IntersectionObserver | null>(null);
  const targets = useRef(new Map<Element, string>());

  useEffect(() => {
    const stop = tracker.start();
    const onVisibility = () => {
      const visible = document.visibilityState === "visible";
      attention.setDocumentVisible(visible);
      if (!visible) tracker.flushWithBeacon();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onVisibility);
      stop();
      void tracker.flush();
    };
  }, [attention]);

  const observe = useCallback<Observe>(
    (element, itemId) => {
      if (typeof IntersectionObserver === "undefined") return () => undefined;
      observer.current ??= new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            const id = targets.current.get(entry.target);
            if (id) attention.setIntersecting(id, seenEnough(entry));
          }
        },
        { threshold: THRESHOLDS },
      );
      targets.current.set(element, itemId);
      observer.current.observe(element);
      return () => {
        observer.current?.unobserve(element);
        targets.current.delete(element);
        attention.release(itemId);
      };
    },
    [attention],
  );

  return <ObserveContext.Provider value={observe}>{children}</ObserveContext.Provider>;
}

/** A ref callback for a story's root element that reports impressions and dwell time. */
export function useStoryTracking(itemId: string) {
  const observe = useContext(ObserveContext);
  return useCallback(
    (element: HTMLElement | null) => (element && observe ? observe(element, itemId) : undefined),
    [observe, itemId],
  );
}
