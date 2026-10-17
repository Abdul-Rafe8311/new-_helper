"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useReducer, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api, type Taxonomy } from "@/lib/api";

import { FINALE, canAdvance, progress, reducer, stepPayload, type Draft } from "./machine";
import { BeatsStep } from "./beats-step";
import { NameStep } from "./name-step";
import { ReadingStep } from "./reading-step";
import { TasteStep } from "./taste-step";
import { WordsStep } from "./words-step";

type Props = {
  initial: Draft;
  taxonomy: Taxonomy;
  /** ISO timestamp from the server, so the masthead date agrees with the rest of the page */
  today: string;
};

const NEXT_LABEL: Record<number, string> = { 5: "Print my first edition" };

export function OnboardingFlow({ initial, taxonomy, today }: Props) {
  const [draft, dispatch] = useReducer(reducer, initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direction, setDirection] = useState<1 | -1>(1);
  const reduceMotion = useReducedMotion();

  const onFinale = draft.step === FINALE;

  async function advance(event?: FormEvent) {
    event?.preventDefault();
    if (saving || !canAdvance(draft)) return;
    const payload = stepPayload(draft, draft.step);
    setSaving(true);
    setError(null);
    try {
      if (payload) await api.onboarding.saveStep(draft.step, payload);
      setDirection(1);
      dispatch({ type: "next" });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function goBack() {
    setError(null);
    setDirection(-1);
    dispatch({ type: "back" });
  }

  const slide = reduceMotion ? 0 : 24;

  return (
    <div className="flex flex-col gap-6">
      <div
        role="progressbar"
        aria-label="Setup progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress(draft) * 100)}
        className="h-1.5 w-full bg-paper-2"
      >
        <motion.div
          className="h-full bg-accent"
          initial={false}
          animate={{ width: `${progress(draft) * 100}%` }}
          transition={{ duration: reduceMotion ? 0 : 0.4, ease: "easeOut" }}
        />
      </div>

      <form noValidate onSubmit={advance} className="flex flex-col gap-8">
        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={draft.step}
            custom={direction}
            initial={{ opacity: 0, x: slide * direction }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -slide * direction }}
            transition={{ duration: reduceMotion ? 0 : 0.22 }}
          >
            {draft.step === 1 ? <NameStep draft={draft} dispatch={dispatch} today={today} /> : null}
            {draft.step === 2 ? <BeatsStep draft={draft} dispatch={dispatch} taxonomy={taxonomy} /> : null}
            {draft.step === 4 ? <TasteStep draft={draft} dispatch={dispatch} /> : null}
            {draft.step === 5 ? <ReadingStep draft={draft} dispatch={dispatch} /> : null}
            {draft.step === 3 ? <WordsStep draft={draft} dispatch={dispatch} taxonomy={taxonomy} /> : null}
          </motion.div>
        </AnimatePresence>

        {error ? (
          <p role="alert" className="border-l-2 border-destructive pl-3 font-sans text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {onFinale ? null : (
          <nav aria-label="Setup steps" className="flex items-center justify-between gap-3">
            <Button type="button" variant="ghost" onClick={goBack} disabled={draft.step === 1 || saving}>
              <ArrowLeft aria-hidden="true" />
              Back
            </Button>
            <Button type="submit" variant="accent" size="lg" disabled={!canAdvance(draft) || saving}>
              {saving ? "Saving…" : (NEXT_LABEL[draft.step] ?? "Continue")}
              <ArrowRight aria-hidden="true" />
            </Button>
          </nav>
        )}
      </form>
    </div>
  );
}
