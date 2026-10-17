import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { PageFrame } from "@/components/reader/page-frame";
import { SideNav } from "@/components/reader/side-nav";
import { getSession } from "@/lib/server/session";

export const metadata: Metadata = { title: "Settings" };

const SHORTCUTS: [string, string][] = [
  ["j / k", "Next / previous story"],
  ["Enter", "Open the focused story"],
  ["o", "Open the original in a new tab"],
  ["s", "Save for later"],
  ["m / l", "More / less like this"],
  ["x", "Skip"],
  ["Shift + A", "Mark everything shown as read"],
];

export default function SettingsPage() {
  return (
    <Suspense fallback={<div aria-busy="true" className="mx-auto mt-10 h-64 w-full max-w-2xl animate-pulse bg-paper-2" />}>
      <Settings />
    </Suspense>
  );
}

async function Settings() {
  const session = await getSession();
  if (!session) redirect("/login");
  const { user, profile } = session;
  return (
    <PageFrame nav={<SideNav base="/today" />}>
    <div className="max-w-2xl space-y-10 py-4">
      <h1 className="font-sans text-[clamp(2.25rem,6.2vw,4.5rem)] leading-none font-extrabold tracking-tight">Settings</h1>
      <section>
        <h2 className="mb-4 font-sans text-sm font-bold tracking-wide text-muted uppercase">Your account</h2>
        <dl className="grid grid-cols-[8rem_1fr] gap-y-2 font-sans text-sm">
          <dt className="text-muted">Name</dt>
          <dd>{user.display_name}</dd>
          <dt className="text-muted">Email</dt>
          <dd>{user.email}</dd>
          <dt className="text-muted">Paper</dt>
          <dd>{profile.paper_name ?? "Not named yet"}</dd>
          <dt className="text-muted">Time zone</dt>
          <dd>{user.timezone}</dd>
          <dt className="text-muted">City</dt>
          <dd>{user.city ?? "Not set"}</dd>
        </dl>
        <p className="mt-4 font-serif text-sm text-muted">
          What goes in your paper lives under{" "}
          <Link href="/interests" className="text-accent underline underline-offset-2">
            Interests
          </Link>
          .
        </p>
      </section>
      <section>
        <h2 className="mb-4 font-sans text-sm font-bold tracking-wide text-muted uppercase">Keyboard shortcuts</h2>
        <dl className="space-y-2 font-sans text-sm">
          {SHORTCUTS.map(([keys, what]) => (
            <div key={keys} className="flex items-baseline gap-4">
              <dt className="w-24 shrink-0">
                <kbd className="rounded border border-rule bg-paper-2 px-1.5 py-0.5 text-xs">{keys}</kbd>
              </dt>
              <dd className="text-muted">{what}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
    </PageFrame>
  );
}
