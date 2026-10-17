"use client";

import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
  type PanInfo,
} from "framer-motion";
import { Check, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { api, type Headline } from "@/lib/api";

import { StepHeading } from "./step-heading";
import type { StepProps } from "./steps-props";

const SWIPE_DISTANCE = 90;
const SEND_ATTEMPTS = 3;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function TasteStep({ draft, dispatch }: StepProps) {
  const [headlines, setHeadlines] = useState<Headline[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [notSaved, setNotSaved] = useState(false);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const group = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.onboarding
      .headlines()
      .then((r) => {
        if (cancelled) return;
        setHeadlines(r.headlines);
        dispatch({ type: "set_taste_total", total: r.headlines.length });
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "We couldn't load today's headlines.");
      });
    return () => {
      cancelled = true;
    };
  }, [dispatch, attempt]);

  const current = headlines?.find((h) => draft.answers[h.id] === undefined) ?? null;
  const answered = headlines ? headlines.filter((h) => draft.answers[h.id] !== undefined).length : 0;
  const liked = headlines ? headlines.filter((h) => draft.answers[h.id] === true).length : 0;

  const answer = useCallback(
    (headline: Headline, interested: boolean) => {
      setDirection(interested ? 1 : -1);
      dispatch({ type: "answer", articleId: headline.id, interested });
      // answers go out one at a time, in order, and retry a couple of times before giving up
      queue.current = queue.current.then(async () => {
        for (let i = 0; i < SEND_ATTEMPTS; i++) {
          try {
            await api.onboarding.answer(headline.id, interested);
            return;
          } catch {
            await wait(400 * (i + 1));
          }
        }
        setNotSaved(true);
      });
      group.current?.focus({ preventScroll: true });
    },
    [dispatch],
  );

  function onKeyDown(event: KeyboardEvent) {
    if (!current) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      answer(current, true);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      answer(current, false);
    }
  }

  return (
    <section>
      <StepHeading
        step={4}
        title="A quick taste test"
        lede="Real headlines from today. Swipe right or tap Interested for more like it, left for less."
      />

      {error ? (
        <div role="alert" className="space-y-3 py-6">
          <p className="font-sans text-sm text-destructive">{error}</p>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setError(null);
              setAttempt((n) => n + 1);
            }}
          >
            Try again
          </Button>
        </div>
      ) : headlines === null ? (
        <div aria-busy="true" aria-label="Loading headlines" className="mx-auto max-w-md space-y-3">
          <div className="aspect-[16/10] animate-pulse bg-paper-2" />
          <div className="h-8 w-4/5 animate-pulse bg-paper-2" />
        </div>
      ) : headlines.length === 0 ? (
        <p className="border-y border-rule py-6 font-serif text-lg text-muted">
          There are no fresh headlines to test yet. Your paper will learn from what you read instead. Continue
          whenever you&apos;re ready.
        </p>
      ) : (
        <div
          ref={group}
          role="group"
          aria-label="Headline taste test"
          tabIndex={0}
          onKeyDown={onKeyDown}
          className="mx-auto max-w-md rounded-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <p role="status" className="mb-3 text-center font-sans text-sm text-muted">
            {current ? `${answered + 1} of ${headlines.length}` : `All ${headlines.length} answered`}
          </p>

          <div className="relative min-h-[26rem]">
            <AnimatePresence mode="popLayout" initial={false} custom={direction}>
              {current ? (
                <HeadlineCard
                  key={current.id}
                  headline={current}
                  direction={direction}
                  onAnswer={(interested) => answer(current, interested)}
                />
              ) : (
                <motion.div
                  key="done"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="border-y-2 border-ink py-10 text-center"
                >
                  <p className="font-display text-3xl font-black">Got it.</p>
                  <p className="mt-2 font-serif text-lg text-muted">
                    You liked {liked} of {headlines.length}. We&apos;ll use that to set your front page.
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Button
              type="button"
              variant="outline"
              size="lg"
              disabled={!current}
              onClick={() => current && answer(current, false)}
            >
              <X aria-hidden="true" />
              Not for me
            </Button>
            <Button
              type="button"
              variant="accent"
              size="lg"
              disabled={!current}
              onClick={() => current && answer(current, true)}
            >
              <Check aria-hidden="true" />
              Interested
            </Button>
          </div>
          <p className="mt-3 text-center font-sans text-xs text-muted">Tip: use the ← and → keys.</p>
        </div>
      )}

      {notSaved ? (
        <p role="status" className="mt-4 font-sans text-xs text-muted">
          A few answers didn&apos;t save, but your paper will still be built from the rest.
        </p>
      ) : null}
    </section>
  );
}

function HeadlineCard({
  headline,
  direction,
  onAnswer,
}: {
  headline: Headline;
  direction: 1 | -1;
  onAnswer: (interested: boolean) => void;
}) {
  const reduceMotion = useReducedMotion();
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-160, 0, 160], [-8, 0, 8]);
  const yes = useTransform(x, [20, 120], [0, 1]);
  const no = useTransform(x, [-120, -20], [1, 0]);

  function onDragEnd(_: unknown, info: PanInfo) {
    if (info.offset.x > SWIPE_DISTANCE) onAnswer(true);
    else if (info.offset.x < -SWIPE_DISTANCE) onAnswer(false);
  }

  return (
    <motion.article
      data-testid="taste-card"
      drag="x"
      dragSnapToOrigin
      dragElastic={0.7}
      onDragEnd={onDragEnd}
      style={{ x, rotate }}
      custom={direction}
      initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{
        x: reduceMotion ? 0 : direction * 420,
        opacity: 0,
        transition: { duration: reduceMotion ? 0 : 0.22 },
      }}
      className="absolute inset-x-0 top-0 cursor-grab touch-pan-y overflow-hidden rounded-sm border border-ink bg-paper active:cursor-grabbing"
    >
      <CardImage url={headline.image_url} />
      <div className="space-y-2 p-4">
        <p className="kicker text-accent">{headline.source}</p>
        <h3 className="font-display text-2xl leading-tight font-black text-balance">{headline.headline}</h3>
      </div>
      <motion.span
        aria-hidden="true"
        style={{ opacity: yes }}
        className="pointer-events-none absolute top-4 left-4 -rotate-6 rounded-sm border-2 border-accent bg-paper px-2 py-1 font-sans text-sm font-bold tracking-widest text-accent uppercase"
      >
        Interested
      </motion.span>
      <motion.span
        aria-hidden="true"
        style={{ opacity: no }}
        className="pointer-events-none absolute top-4 right-4 rotate-6 rounded-sm border-2 border-ink bg-paper px-2 py-1 font-sans text-sm font-bold tracking-widest uppercase"
      >
        Not for me
      </motion.span>
    </motion.article>
  );
}

function CardImage({ url }: { url: string | null | undefined }) {
  const [broken, setBroken] = useState(false);
  if (!url || broken) {
    return <div aria-hidden="true" className="halftone aspect-[16/10] w-full" />;
  }
  return (
    // Publisher images come from arbitrary hosts, so next/image's allow-list does not apply.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt=""
      loading="eager"
      draggable={false}
      referrerPolicy="no-referrer"
      onError={() => setBroken(true)}
      className="aspect-[16/10] w-full object-cover"
    />
  );
}
