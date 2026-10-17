import { redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { AppHeader, AppHeaderSkeleton } from "@/components/shell/app-header";
import { getSession } from "@/lib/server/session";

/** Signed-in area. The session is read per request, so it streams in behind Suspense. */
export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<AppHeaderSkeleton />}>
      <SignedIn>{children}</SignedIn>
    </Suspense>
  );
}

async function SignedIn({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!session.profile.onboarding_completed) redirect("/onboarding");
  return (
    <>
      <AppHeader session={session} now={new Date()} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </>
  );
}
