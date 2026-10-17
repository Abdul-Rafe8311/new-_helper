"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PrintingPress } from "@/components/onboarding/printing-press";
import { Button } from "@/components/ui/button";
import { ApiError, api, type Edition } from "@/lib/api";

import { useActiveEdition } from "./chrome-context";

export const POLL_MS = 5000;

const STAGE_TEXT: Record<string, string> = {
  gathering: "Gathering the day's stories…",
  choosing: "Choosing what matters to you…",
  writing: "Writing your headlines…",
  typesetting: "Typesetting the front page…",
};

type Phase = "missing" | "starting" | "pending" | "failed";

function phaseOf(edition: Edition | null): Phase {
  if (!edition) return "missing";
  return edition.status === "failed" ? "failed" : "pending";
}

/**
 * Today's paper is not ready: show the printing press and poll /api/editions/today every 5s
 * until it is, then ask the server to render it. If there is no paper at all, offer to print one.
 */
export function EditionPending({ initial }: { initial: Edition | null }) {
  const router = useRouter();
  const [edition, setEdition] = useState<Edition | null>(initial);
  const [phase, setPhase] = useState<Phase>(phaseOf(initial));
  const [error, setError] = useState<string | null>(null);
  useActiveEdition(null);

  useEffect(() => {
    if (phase !== "pending" && phase !== "starting") return;
    const timer = setInterval(async () => {
      try {
        const latest = await api.editions.today();
        setEdition(latest);
        if (latest.status === "ready") router.refresh();
        else if (latest.status === "failed") setPhase("failed");
        else setPhase("pending");
      } catch (e) {
        // not there yet while it is starting, or a hiccup: keep polling
        if (e instanceof ApiError && e.status === 401) router.refresh();
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [phase, router]);

  const print = useCallback(async () => {
    setError(null);
    setPhase("starting");
    try {
      setEdition(await api.editions.regenerate());
      setPhase("pending");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "We couldn't start your paper.");
      setPhase(edition ? "failed" : "missing");
    }
  }, [edition]);

  const stage = typeof edition?.stats?.stage === "string" ? edition.stats.stage : null;

  if (phase === "pending" || phase === "starting") {
    return (
      <section aria-live="polite" className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center px-4 py-16 text-center">
        <PrintingPress />
        <h1 className="mt-6 font-display text-3xl font-black">Your paper is on the press</h1>
        <p role="status" className="mt-2 font-serif text-lg text-muted">
          {(stage && STAGE_TEXT[stage]) || "Setting the type…"}
        </p>
        <p className="mt-1 font-sans text-xs text-muted">This page updates by itself. It usually takes a minute or two.</p>
      </section>
    );
  }

  return (
    <section className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="font-display text-3xl font-black">
        {phase === "failed" ? "The press jammed" : "No paper yet today"}
      </h1>
      <p className="mt-2 font-serif text-lg text-muted">
        {phase === "failed"
          ? "Something went wrong while printing your edition. Try again."
          : "Your morning edition hasn't been printed yet."}
      </p>
      {error ? (
        <p role="alert" className="mt-3 font-sans text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <Button className="mt-6" onClick={() => void print()}>
        {phase === "failed" ? "Try again" : "Print today's paper"}
      </Button>
    </section>
  );
}
