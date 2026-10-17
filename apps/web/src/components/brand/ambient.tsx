import type { CSSProperties } from "react";

import { FRONT_COLOR } from "@/components/reader/palette";

/** The reader's soft colour glow, held still for pages outside the reader (landing, sign-in, onboarding). */
export function StaticAmbient({ color = FRONT_COLOR }: { color?: string }) {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="ambient-layer" data-on="true" style={{ "--glow": color } as CSSProperties} />
    </div>
  );
}
