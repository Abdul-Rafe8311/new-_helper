import { redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { AppHeader, AppHeaderSkeleton } from "@/components/shell/app-header";
import { getSession } from "@/lib/server/session";

/** Onboarding needs a session but not a finished profile, so it lives outside the (app) group. */
export default function OnboardingLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<AppHeaderSkeleton />}>
      <SignedIn>{children}</SignedIn>
    </Suspense>
  );
}

async function SignedIn({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login?next=/onboarding");
  return (
    <>
      <AppHeader session={session} now={new Date()} showNav={false} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </>
  );
}
