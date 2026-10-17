import { notFound, redirect } from "next/navigation";

import { quizEnabled } from "@/lib/config";
import { loadEdition } from "@/lib/server/editions";
import { getSession } from "@/lib/server/session";

import { EditionPending } from "./edition-pending";
import { EditionWorkspace } from "./edition-workspace";
import { PageFrame } from "./page-frame";
import { previousDay, questionsOf, recallFrom } from "./quiz/model";
import { SideNav } from "./side-nav";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Server component: fetch one edition and hand it to the reader (or the printing press). */
export async function EditionPage({ date, basePath }: { date: "today" | string; basePath: string }) {
  if (date !== "today" && !DATE.test(date)) notFound();
  const session = await getSession();
  if (!session) redirect("/login");
  const edition = await loadEdition(date);

  if (date === "today" && (!edition || edition.status !== "ready")) {
    return (
      <PageFrame nav={<SideNav base={basePath} />}>
        <EditionPending initial={edition} />
      </PageFrame>
    );
  }
  if (!edition || edition.status !== "ready") {
    return (
      <PageFrame nav={<SideNav base={basePath} />}>
        <section className="mx-auto max-w-md py-16 text-center">
          <h1 className="font-sans text-3xl font-extrabold">No paper for that day</h1>
          <p className="mt-2 font-serif text-lg text-muted">There is no finished edition for {date}.</p>
        </section>
      </PageFrame>
    );
  }
  // The quiz belongs to today's paper only: answering an old one must not backfill the streak.
  const withQuiz = date === "today" && quizEnabled();
  // A hiccup fetching yesterday's paper must not cost the reader today's.
  const yesterday = withQuiz ? await loadEdition(previousDay(edition.date)).catch(() => null) : null;
  return (
    <EditionWorkspace
      quiz={withQuiz ? questionsOf(edition) : []}
      recall={withQuiz ? recallFrom(edition.date, yesterday) : null}
      edition={edition}
      timeZone={session.user.timezone}
      now={new Date().toISOString()}
      basePath={basePath}
    />
  );
}
