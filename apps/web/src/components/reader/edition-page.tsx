import { notFound, redirect } from "next/navigation";

import { loadEdition } from "@/lib/server/editions";
import { getSession } from "@/lib/server/session";

import { paperNameFor } from "@/components/shell/app-header";

import { EditionPending } from "./edition-pending";
import { EditionWorkspace } from "./edition-workspace";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Server component: fetch one edition and hand it to the reader (or the printing press). */
export async function EditionPage({
  date,
  sectionsPanel,
}: {
  date: "today" | string;
  sectionsPanel: boolean;
}) {
  if (date !== "today" && !DATE.test(date)) notFound();
  const session = await getSession();
  if (!session) redirect("/login");
  const edition = await loadEdition(date);

  if (date === "today" && (!edition || edition.status !== "ready")) return <EditionPending initial={edition} />;
  if (!edition || edition.status !== "ready") {
    return (
      <section className="mx-auto max-w-md flex-1 px-4 py-16 text-center">
        <h1 className="font-display text-3xl font-black">No paper for that day</h1>
        <p className="mt-2 font-serif text-lg text-muted">There is no finished edition for {date}.</p>
      </section>
    );
  }
  return (
    <EditionWorkspace
      edition={edition}
      paperName={edition.title ?? paperNameFor(session)}
      timeZone={session.user.timezone}
      now={new Date().toISOString()}
      sectionsPanel={sectionsPanel}
    />
  );
}
