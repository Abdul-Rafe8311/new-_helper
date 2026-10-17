"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { pdfHref } from "@/lib/api";

import { useChrome } from "./chrome-context";

type Phase = "idle" | "loading" | "error";

function filenameFrom(header: string | null, fallback: string): string {
  return /filename="?([^";]+)"?/.exec(header ?? "")?.[1] ?? fallback;
}

/**
 * "Download newspaper": the PDF of the edition on screen (or today's). Typesetting can take a few
 * seconds the first time, so the button shows progress and a retryable error instead of waiting
 * silently on a navigation.
 */
export function DownloadButton({ defaultDate }: { defaultDate: string }) {
  const { edition } = useChrome();
  const [phase, setPhase] = useState<Phase>("idle");
  const date = edition?.date ?? defaultDate;
  const disabled = phase === "loading" || (edition !== null && !edition.ready);

  async function download() {
    setPhase("loading");
    try {
      const response = await fetch(pdfHref(date), { credentials: "same-origin" });
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filenameFrom(response.headers.get("Content-Disposition"), `newspaper-${date}.pdf`);
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      setPhase("idle");
    } catch {
      setPhase("error");
    }
  }

  return (
    <div className="relative">
      <Button
        variant="accent"
        size="lg"
        disabled={disabled}
        aria-busy={phase === "loading"}
        onClick={() => void download()}
        className="press h-10 rounded-full px-3 font-semibold sm:px-5"
      >
        {phase === "loading" ? <Loader2 aria-hidden="true" className="animate-spin" /> : <Download aria-hidden="true" />}
        <span className="hidden sm:inline">{phase === "loading" ? "Preparing…" : "Download newspaper"}</span>
        <span className="sm:hidden">{phase === "loading" ? "…" : "PDF"}</span>
        <span className="sr-only sm:hidden">{phase === "loading" ? "Preparing the newspaper" : "Download newspaper"}</span>
      </Button>
      {phase === "error" ? (
        <p
          role="alert"
          className="absolute top-full right-0 z-40 mt-2 w-60 rounded-md border border-rule bg-surface p-3 font-sans text-xs shadow-lg"
        >
          We couldn&apos;t prepare that edition&apos;s PDF.{" "}
          <button type="button" className="font-semibold text-accent underline" onClick={() => void download()}>
            Try again
          </button>
        </p>
      ) : null}
    </div>
  );
}
