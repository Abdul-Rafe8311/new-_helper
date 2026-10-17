import { X } from "lucide-react";
import Link from "next/link";

import { MASCOTS, Portrait } from "@/components/landing/mascots";

import "./auth.css";

/** Where each decorative portrait sits on the art panel: left/top in %, and a size in px. */
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

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="su-stage">
      <div className="su-art" aria-hidden="true">
        {ART.map((tile, i) => (
          <span
            key={i}
            className="su-art__tile"
            style={{ left: `${tile.x}%`, top: `${tile.y}%`, width: tile.w, height: tile.w * 1.25 }}
          >
            <Portrait mascot={MASCOTS[(i * 5) % MASCOTS.length]} index={(i * 5) % MASCOTS.length} />
          </span>
        ))}
      </div>
      <div className="su-card">
        <header className="su-card__head">
          <Link href="/" className="su-brand">
            NewsHelper
          </Link>
          <Link href="/" className="su-close" aria-label="Close and go back home">
            <X aria-hidden="true" />
          </Link>
        </header>
        <main className="su-card__body">{children}</main>
      </div>
    </div>
  );
}
