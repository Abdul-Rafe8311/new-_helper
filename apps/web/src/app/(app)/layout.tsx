import { redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { ReaderChrome, ReaderChromeSkeleton } from "@/components/reader/reader-chrome";
import { getSession } from "@/lib/server/session";

/** Signed-in area. The session is read per request, so it streams in behind Suspense. */
export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<ReaderChromeSkeleton />}>
      <SignedIn>{children}</SignedIn>
    </Suspense>
  );
}

async function SignedIn({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!session.profile.onboarding_completed) redirect("/onboarding");
  return (
    <ReaderChrome session={session}>
      <main id="main" className="flex flex-1 flex-col">
        {children}
      </main>
    </ReaderChrome>
  );
}
