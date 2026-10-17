"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api, type OnboardingState, type Taxonomy } from "@/lib/api";

import { hydrate, initialDraft, type Draft } from "./machine";
import { OnboardingFlow } from "./onboarding-flow";

type Props = {
  displayName: string;
  timezone: string;
  city: string | null;
  today: string;
};

type Loaded = { draft: Draft; taxonomy: Taxonomy };

function detectTimeZone(fallback: string): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || fallback;
  } catch {
    return fallback;
  }
}

/** Loads the taxonomy and whatever the reader already saved, then hands over to the flow. */
export function OnboardingLoader({ displayName, timezone, city, today }: Props) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [taxonomy, saved]: [Taxonomy, OnboardingState] = await Promise.all([
          api.taxonomy(),
          api.onboarding.state(),
        ]);
        if (cancelled) return;
        // a saved name step already carries the time zone the reader confirmed
        const base = initialDraft({ displayName, timezone: detectTimeZone(timezone), city });
        setLoaded({ draft: hydrate(base, saved), taxonomy });
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "We couldn't load your setup.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [displayName, timezone, city, attempt]);

  if (loaded) return <OnboardingFlow initial={loaded.draft} taxonomy={loaded.taxonomy} today={today} />;

  if (error) {
    return (
      <div role="alert" className="space-y-3 py-10 text-center">
        <p className="font-sans text-sm text-destructive">{error}</p>
        <Button
          variant="outline"
          onClick={() => {
            setError(null);
            setAttempt((n) => n + 1);
          }}
        >
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div aria-busy="true" aria-label="Loading your setup" className="space-y-4 py-4">
      <div className="h-1.5 w-full animate-pulse bg-paper-2" />
      <div className="h-8 w-2/3 animate-pulse bg-paper-2" />
      <div className="h-40 w-full animate-pulse bg-paper-2" />
    </div>
  );
}
