"use client";

import { ChevronLeft, ChevronRight, Images, X } from "lucide-react";
import Image from "next/image";
import { Dialog } from "radix-ui";
import { useState } from "react";

import type { StoryImage } from "@/lib/api";

const NAV =
  "absolute top-1/2 inline-flex size-12 -translate-y-1/2 items-center justify-center rounded-full bg-black/55 text-white outline-none hover:bg-black/75 focus-visible:ring-[3px] focus-visible:ring-white disabled:opacity-30";

/**
 * "View photos": a full-screen gallery. The dialog traps focus, closes on Escape and gives focus
 * back to the button; the arrow keys (and buttons) move between pictures.
 */
export function PhotoGallery({ images, headline }: { images: StoryImage[]; headline: string }) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  if (images.length === 0) return null;
  const last = images.length - 1;
  const image = images[index];
  const go = (to: number) => setIndex(Math.min(last, Math.max(0, to)));

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setIndex(0);
      }}
    >
      <Dialog.Trigger className="press inline-flex h-10 items-center gap-2 rounded-full border border-rule bg-surface px-4 font-sans text-sm font-semibold outline-none hover:bg-paper-2 focus-visible:ring-[3px] focus-visible:ring-ring/50">
        <Images aria-hidden="true" className="size-4" />
        View photos
        <span className="text-muted">({images.length})</span>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/90" />
        <Dialog.Content
          aria-describedby={undefined}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") go(index + 1);
            if (event.key === "ArrowLeft") go(index - 1);
          }}
          className="fixed inset-0 z-50 flex flex-col p-4 text-white outline-none sm:p-8"
        >
          <div className="flex items-center justify-between gap-4">
            <Dialog.Title className="line-clamp-1 font-sans text-base font-semibold">{headline}</Dialog.Title>
            <Dialog.Close
              aria-label="Close gallery"
              className="inline-flex size-11 items-center justify-center rounded-full bg-white/10 outline-none hover:bg-white/20 focus-visible:ring-[3px] focus-visible:ring-white"
            >
              <X aria-hidden="true" />
            </Dialog.Close>
          </div>
          <div className="relative my-4 min-h-0 flex-1">
            <Image
              key={image.url}
              src={image.url}
              alt={`Photo ${index + 1} of ${images.length}, from ${image.credit}`}
              fill
              unoptimized
              sizes="100vw"
              className="object-contain"
            />
            <button type="button" aria-label="Previous photo" disabled={index === 0} onClick={() => go(index - 1)} className={`${NAV} left-0`}>
              <ChevronLeft aria-hidden="true" />
            </button>
            <button type="button" aria-label="Next photo" disabled={index === last} onClick={() => go(index + 1)} className={`${NAV} right-0`}>
              <ChevronRight aria-hidden="true" />
            </button>
          </div>
          <p role="status" className="text-center font-sans text-sm text-white/80">
            Photo {index + 1} of {images.length} · Credit: {image.credit}
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
