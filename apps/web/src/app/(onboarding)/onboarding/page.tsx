import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { OnboardingLoader } from "@/components/onboarding/onboarding-loader";
import { getSession } from "@/lib/server/session";

export const metadata: Metadata = { title: "Set up your paper" };

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div aria-busy="true" className="h-64 animate-pulse bg-paper-2" />}>
      <Onboarding />
    </Suspense>
  );
}

async function Onboarding() {
  const session = await getSession();
  if (!session) redirect("/login?next=/onboarding");
  if (session.profile.onboarding_completed) redirect("/today");
  return (
    <OnboardingLoader
      displayName={session.user.display_name}
      timezone={session.user.timezone}
      city={session.user.city ?? null}
      today={new Date().toISOString()}
    />
  );
}
