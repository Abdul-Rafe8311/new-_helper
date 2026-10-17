"use client";

import { useId, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, type Taxonomy } from "@/lib/api";

import { RemovableChip } from "./chip";
import { EMPTY_PARSED, heardChips, normaliseParsed, type Chip } from "./machine";
import { StepHeading } from "./step-heading";
import type { StepProps } from "./steps-props";

export const WORDS_PLACEHOLDER =
  "I run a digital agency, follow AI agents, Pakistani cricket and F1, and skip celebrity gossip";

export function WordsStep({ draft, dispatch, taxonomy }: StepProps & { taxonomy: Taxonomy }) {
  const textId = useId();
  const addId = useId();
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extra, setExtra] = useState("");

  const labels = new Map(taxonomy.topics.map((t) => [t.slug, t.label]));
  const labelOf = (chip: Chip) =>
    chip.kind === "topic" || chip.kind === "blocked_topic" ? (labels.get(chip.value) ?? chip.value) : chip.value;

  const hasText = draft.text.trim().length > 0;

  async function readIt() {
    if (!hasText || parsing) return;
    setParsing(true);
    setError(null);
    try {
      dispatch({ type: "set_parsed", parsed: normaliseParsed(await api.onboarding.parse(draft.text.trim())) });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "We couldn't read that. Check your connection and try again.");
    } finally {
      setParsing(false);
    }
  }

  function onTextKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      void readIt();
    }
  }

  function addExtra() {
    dispatch({ type: "add_keyword", keyword: extra });
    setExtra("");
  }

  const { heard, not } = draft.parsed ? heardChips(draft.parsed) : { heard: [], not: [] };

  return (
    <section>
      <StepHeading
        step={3}
        title="In your own words"
        lede="Tell us what you want to read, and what you don't. We'll turn it into topics you can edit."
      />

      <div className="space-y-2">
        <Label htmlFor={textId}>What should your paper be about?</Label>
        <textarea
          id={textId}
          value={draft.text}
          rows={4}
          maxLength={1500}
          placeholder={WORDS_PLACEHOLDER}
          onChange={(e) => dispatch({ type: "set_text", text: e.target.value })}
          onKeyDown={onTextKey}
          className="w-full resize-y rounded-sm border border-input bg-paper px-3 py-2 font-serif text-lg leading-snug shadow-xs outline-none placeholder:text-muted focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <p className="font-sans text-xs text-muted">Optional. Press Ctrl or ⌘ + Enter to read it.</p>
      </div>

      {!draft.parsed ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" disabled={!hasText || parsing} onClick={() => void readIt()}>
            {parsing ? "Reading…" : "Show me what you heard"}
          </Button>
          {!hasText ? <span className="font-sans text-sm text-muted">Or just continue; you can skip this.</span> : null}
          {hasText ? (
            <button
              type="button"
              className="font-sans text-sm text-muted underline underline-offset-4"
              onClick={() => dispatch({ type: "set_parsed", parsed: EMPTY_PARSED })}
            >
              Continue without
            </button>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="mt-4 border-l-2 border-destructive pl-3 font-sans text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {draft.parsed && (hasText || heard.length > 0) ? (
        <div className="mt-6 space-y-4 border-t border-rule pt-5" aria-live="polite">
          <p className="font-serif text-lg">
            <span className="font-display font-black">We heard:</span>{" "}
            {heard.length ? heard.map(labelOf).join(", ") : "nothing yet"}.
            {not.length ? (
              <>
                {" "}
                <span className="font-display font-black">Not:</span> {not.map(labelOf).join(", ")}.
              </>
            ) : null}
          </p>
          <p className="font-sans text-xs text-muted">Remove anything we got wrong, or add what we missed.</p>

          {heard.length ? (
            <ul className="flex flex-wrap gap-2" aria-label="What we heard">
              {heard.map((chip) => (
                <li key={`${chip.kind}-${chip.value}`}>
                  <RemovableChip label={labelOf(chip)} onRemove={() => dispatch({ type: "remove_chip", chip })} />
                </li>
              ))}
            </ul>
          ) : null}
          {not.length ? (
            <ul className="flex flex-wrap gap-2" aria-label="What to skip">
              {not.map((chip) => (
                <li key={`${chip.kind}-${chip.value}`}>
                  <RemovableChip
                    tone="not"
                    label={`Not ${labelOf(chip)}`}
                    onRemove={() => dispatch({ type: "remove_chip", chip })}
                  />
                </li>
              ))}
            </ul>
          ) : null}

          <div className="flex max-w-md gap-2">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor={addId} className="sr-only">
                Add something we missed
              </Label>
              <Input
                id={addId}
                value={extra}
                maxLength={80}
                placeholder="Add something we missed"
                onChange={(e) => setExtra(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addExtra();
                  }
                }}
              />
            </div>
            <Button type="button" variant="outline" disabled={!extra.trim()} onClick={addExtra}>
              Add
            </Button>
          </div>
          <button
            type="button"
            className="font-sans text-sm text-muted underline underline-offset-4"
            disabled={parsing}
            onClick={() => void readIt()}
          >
            {parsing ? "Reading…" : "Read it again"}
          </button>
        </div>
      ) : null}
    </section>
  );
}
