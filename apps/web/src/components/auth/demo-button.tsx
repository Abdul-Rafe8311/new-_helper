"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

/** Signs into the shared demo account and opens today's paper. */
export function DemoButton({ className }: { className?: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function tryDemo() {
    setError(null);
    startTransition(async () => {
      try {
        await api.auth.demo();
        router.push("/today");
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "The demo is unavailable right now.");
      }
    });
  }

  return (
    <div className={className}>
      <Button variant="outline" size="lg" onClick={tryDemo} disabled={pending}>
        {pending ? "Opening the demo…" : "Try the demo"}
      </Button>
      {error ? (
        <p role="alert" className="mt-2 font-sans text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
