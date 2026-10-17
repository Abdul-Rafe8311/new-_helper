"use client";

import { useEffect, useState } from "react";

import { api, type QuizStreak } from "@/lib/api";

/** The reader's streak as the server counts it; `null` until it arrives (or if it cannot). */
export function useQuizStreak(): QuizStreak | null {
  const [streak, setStreak] = useState<QuizStreak | null>(null);
  useEffect(() => {
    let live = true;
    api
      .quizStreak()
      .then((value) => live && setStreak(value))
      .catch(() => live && setStreak({ streak: 0, done_today: false }));
    return () => {
      live = false;
    };
  }, []);
  return streak;
}
