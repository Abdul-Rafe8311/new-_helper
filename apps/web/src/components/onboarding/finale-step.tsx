"use client";

import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";

import {
  GIVE_UP_MS,
  POLL_MS,
  PRESS_STAGES,
  phaseFromStatus,
  stageIndex,
  type Phase,
} from "./finale";
import { PrintingPress } from "./printing-press";
import { StepHeading } from "./step-heading";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function FinaleStep({ paperName }: { paperName: string }) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "starting" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await api.onboarding.complete();
        const deadline = Date.now() + GIVE_UP_MS;
        let current: Phase = { kind: "printing", stage: "gathering" };
        if (!cancelled) setPhase(current);
        while (!cancelled && Date.now() < deadline) {
          current = phaseFromStatus(await api.onboarding.status(), current);
          if (cancelled) return;
          setPhase(current);
          if (current.kind === "ready") {
            await wait(900);
            if (!cancelled) {
              router.replace("/today");
              router.refresh();
            }
            return;
          }
          if (current.kind === "failed") return;
          await wait(POLL_MS);
        }
        if (!cancelled) setPhase({ kind: "failed", message: "This is taking longer than expected." });
      } catch (e) {
        if (!cancelled) {
          setPhase({
            kind: "failed",
            message: e instanceof ApiError ? e.message : "We lost the connection to the press.",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [attempt, router]);

  const active = phase.kind === "printing" ? stageIndex(phase.stage) : phase.kind === "ready" ? PRESS_STAGES.length : -1;

  return (
    <section className="py-4 text-center">
      <StepHeading
        step={6}
        title={phase.kind === "ready" ? "Stop the presses!" : "Printing your first edition"}
        lede={`${paperName} is going to press.`}
      />

      <PrintingPress />

      <p role="status" aria-live="polite" className="mt-6 font-serif text-xl italic">
        {phase.kind === "printing"
          ? PRESS_STAGES[stageIndex(phase.stage)].message
          : phase.kind === "ready"
            ? "Fresh off the press. Taking you to your paper…"
            : phase.kind === "failed"
              ? phase.message
              : "Warming up the presses…"}
      </p>

      <ol aria-label="Printing progress" className="mx-auto mt-6 flex max-w-md justify-between gap-2">
        {PRESS_STAGES.map((stage, i) => (
          <li
            key={stage.key}
            aria-current={i === active ? "step" : undefined}
            className={cn(
              "flex flex-1 flex-col items-center gap-1 font-sans text-xs",
              i < active ? "text-ink" : i === active ? "font-semibold text-accent" : "text-muted",
            )}
          >
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full border",
                i < active ? "border-ink bg-ink text-paper" : i === active ? "border-accent" : "border-rule",
              )}
            >
              {i < active ? <Check className="size-3.5" aria-hidden="true" /> : i + 1}
            </span>
            {stage.label}
          </li>
        ))}
      </ol>

      {phase.kind === "failed" ? (
        <div className="mt-6 flex justify-center gap-3">
          <Button
            type="button"
            variant="accent"
            onClick={() => {
              setPhase({ kind: "starting" });
              setAttempt((n) => n + 1);
            }}
          >
            Try again
          </Button>
        </div>
      ) : null}
    </section>
  );
}
