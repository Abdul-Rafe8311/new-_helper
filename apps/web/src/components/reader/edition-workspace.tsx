"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { formatDateLine } from "@/components/paper";
import type { Edition } from "@/lib/api";

import { useAccent, useActiveEdition } from "./chrome-context";
import { EditionHeader } from "./edition-header";
import { sectionFromParam, sectionsOf, visibleItems, type ItemStates } from "./model";
import { categoryColor, FRONT_COLOR } from "./palette";
import { PageFrame } from "./page-frame";
import { QuizSection } from "./quiz/quiz-section";
import { RecallCard } from "./quiz/recall-card";
import type { QuizQuestion, Recall } from "./quiz/model";
import { SideNav, type NavCategory } from "./side-nav";
import { StoryGrid } from "./story-grid";
import { UndoToast } from "./toast";
import { useReaderCore } from "./use-reader-core";

type Props = {
  edition: Edition;
  timeZone: string;
  /** Server render time, so relative times agree between server and client. */
  now: string;
  /** Where this edition lives: /today, /paper/[date] or /archive/[date]. */
  basePath: string;
  /** Today's quiz and a question from yesterday's paper; both empty when the quiz is off. */
  quiz?: QuizQuestion[];
  recall?: Recall | null;
};

/** One finished edition: the section is the `?section=` in the URL, so refresh and Back just work. */
export function EditionWorkspace({ edition, timeZone, now, basePath, quiz = [], recall = null }: Props) {
  const sections = useMemo(() => sectionsOf(edition), [edition]);
  const section = sectionFromParam(sections, useSearchParams().get("section"));
  const nowDate = useMemo(() => new Date(now), [now]);
  const categories = useMemo<NavCategory[]>(
    () => sections.map((s) => ({ slug: s.slug, label: s.name, color: categoryColor(s.name) })),
    [sections],
  );
  useActiveEdition({ date: edition.date, ready: edition.status === "ready" });
  useAccent(section ? categoryColor(section.name) : FRONT_COLOR);

  const slug = section?.slug ?? null;
  const choose = useCallback((states: ItemStates) => visibleItems(sections, slug, states), [sections, slug]);
  const core = useReaderCore(choose);

  return (
    <PageFrame nav={<SideNav base={basePath} categories={categories} />}>
      <EditionHeader
        title={section ? section.name : "For You"}
        dateLine={formatDateLine(`${edition.date}T12:00:00Z`, timeZone)}
        kicker={`No. ${edition.number}`}
        note={section ? null : edition.editor_note}
        topics={{ base: basePath, categories, activeSlug: slug }}
      />
      {recall && !section ? <RecallCard recall={recall} /> : null}
      {core.items.length === 0 ? (
        <div className="py-16 text-center">
          <p className="font-sans text-xl font-bold">You&apos;ve seen everything here.</p>
          {section ? (
            <Link href={basePath} className="mt-3 inline-block font-sans text-sm font-semibold text-cat underline underline-offset-4">
              Back to For You
            </Link>
          ) : null}
        </div>
      ) : (
        <StoryGrid items={core.items} core={core} now={nowDate} />
      )}
      <QuizSection questions={quiz} />
      <UndoToast toast={core.toast.toast} onDismiss={core.toast.dismiss} />
    </PageFrame>
  );
}
