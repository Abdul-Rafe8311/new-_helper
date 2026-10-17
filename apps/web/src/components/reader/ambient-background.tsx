"use client";

import { useState } from "react";

import { useChrome } from "./chrome-context";

/**
 * A large, soft colour glow behind the upper-left of the page. Gradients do not interpolate, so a
 * category change crossfades between two stacked layers instead (see `.ambient-layer`).
 */
export function AmbientBackground() {
  const { accent } = useChrome();
  const [layers, setLayers] = useState({ a: accent, b: accent, front: "a" as "a" | "b" });

  const showing = layers.front === "a" ? layers.a : layers.b;
  if (accent !== showing) {
    // derived from props during render, so the new colour starts fading in with no extra paint
    setLayers(
      layers.front === "a" ? { a: layers.a, b: accent, front: "b" } : { a: accent, b: layers.b, front: "a" },
    );
  }

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-0 overflow-hidden">
      <div className="ambient-layer" data-on={layers.front === "a"} style={{ "--glow": layers.a } as React.CSSProperties} />
      <div className="ambient-layer" data-on={layers.front === "b"} style={{ "--glow": layers.b } as React.CSSProperties} />
    </div>
  );
}
