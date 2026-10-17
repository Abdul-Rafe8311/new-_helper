import { X } from "lucide-react";
import Link from "next/link";

import { StaticAmbient } from "@/components/brand/ambient";
import { Brand } from "@/components/brand/brand";
import { MASCOTS, Portrait } from "@/components/landing/mascots";
import { ThemeToggle } from "@/components/theme/theme-toggle";

import "./auth.css";

/** Where each decorative portrait sits on the art panel: left/top in %, and a width in px. */
const ART: readonly { x: number; y: number; w: number }[] = [
  { x: 8, y: 8, w: 84 },
  { x: 30, y: 4, w: 56 },
  { x: 58, y: 10, w: 112 },
  { x: 84, y: 6, w: 64 },
  { x: 14, y: 34, w: 124 },
  { x: 46, y: 32, w: 72 },
  { x: 74, y: 30, w: 96 },
  { x: 6, y: 66, w: 70 },
  { x: 34, y: 62, w: 104 },
  { x: 62, y: 66, w: 64 },
  { x: 82, y: 58, w: 120 },
  { x: 52, y: 86, w: 80 },
];

/** Sign-in and sign-up: the reader's canvas and glow, the shared wordmark, a card, and the cast. */
export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="su-stage brand-scope bg-canvas font-sans text-ink">
      <StaticAmbient />
      <div className="su-art" aria-hidden="true">
        {ART.map((tile, i) => (
          <span key={i} className="su-art__tile" style={{ left: `${tile.x}%`, top: `${tile.y}%`, width: tile.w, height: tile.w * 1.25 }}>
            <Portrait mascot={MASCOTS[(i * 5) % MASCOTS.length]} index={(i * 5) % MASCOTS.length} />
          </span>
        ))}
      </div>
      <div className="su-card card">
        <header className="flex items-center justify-between border-b border-rule py-2 pr-2 pl-5">
          <Brand size="md" />
          <div className="flex items-center">
            <ThemeToggle />
            <Link
              href="/"
              aria-label="Close and go back home"
              className="inline-flex size-10 items-center justify-center rounded-full text-ink outline-none hover:bg-ink/8 focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <X aria-hidden="true" className="size-5" />
            </Link>
          </div>
        </header>
        <main id="main" className="px-6 py-9 sm:px-10 sm:py-11">
          {children}
        </main>
      </div>
    </div>
  );
}
