import Image from "next/image";
import type { CSSProperties } from "react";

import type { StoryImage } from "@/lib/api";

/** Rotation, drift and hover growth for each layer; the growth is capped so layers never collide. */
const LAYERS = [
  { r: "-3deg", x: "0%", y: "0%", grow: 1.06, w: "62%", left: "5%", top: "14%" },
  { r: "5deg", x: "3%", y: "-3%", grow: 1.1, w: "44%", left: "54%", top: "0%" },
  { r: "-6deg", x: "-3%", y: "3%", grow: 1.1, w: "40%", left: "24%", top: "64%" },
  { r: "4deg", x: "3%", y: "3%", grow: 1.12, w: "36%", left: "62%", top: "55%" },
] as const;

/**
 * Up to four of the story's own pictures, overlapping and gently rotated. With one picture it is
 * simply a single large hero image. Hover (fine pointers only) straightens and enlarges layers.
 */
export function PhotoStack({ images }: { images: StoryImage[] }) {
  if (images.length === 0) return null;
  const shown = images.slice(0, 4);

  if (shown.length === 1) {
    return (
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl bg-paper-2 shadow-xl">
        <Image src={shown[0].url} alt="" fill unoptimized priority sizes="(min-width: 1024px) 560px, 100vw" className="object-cover" />
      </div>
    );
  }
  return (
    <div className="photo-stack relative mx-auto aspect-[5/4] w-full max-w-[600px]" data-testid="photo-stack">
      {shown.map((image, i) => {
        const layer = LAYERS[i];
        return (
          <div
            key={image.url}
            className="photo-stack__photo absolute aspect-[4/3] overflow-hidden rounded-2xl bg-paper-2 shadow-[0_12px_32px_-8px_rgba(0,0,0,0.35)]"
            style={
              { "--r": layer.r, "--x": layer.x, "--y": layer.y, "--grow": layer.grow, width: layer.w, left: layer.left, top: layer.top, zIndex: shown.length - i } as CSSProperties
            }
          >
            <Image
              src={image.url}
              alt=""
              fill
              unoptimized
              priority={i === 0}
              sizes="(min-width: 1024px) 340px, 60vw"
              className="object-cover"
            />
          </div>
        );
      })}
    </div>
  );
}
