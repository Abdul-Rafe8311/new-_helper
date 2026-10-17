import { redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { StaticAmbient } from "@/components/brand/ambient";
import { Brand } from "@/components/brand/brand";
import { LogoutButton } from "@/components/shell/logout-button";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { getSession } from "@/lib/server/session";

/** Onboarding needs a session but not a finished profile, so it lives outside the (app) group. */
export default function OnboardingLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<Frame>{null}</Frame>}>
      <SignedIn>{children}</SignedIn>
    </Suspense>
  );
}

async function SignedIn({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login?next=/onboarding");
  return <Frame signedIn>{children}</Frame>;
}

/** The same canvas, glow and wordmark as the reader, so setup feels like part of the product. */
function Frame({ children, signedIn = false }: { children: ReactNode; signedIn?: boolean }) {
  return (
    <div className="brand-scope relative flex min-h-screen flex-col bg-canvas font-sans text-ink">
      <StaticAmbient />
      <header className="relative z-10 mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4 sm:h-20 sm:px-6">
        <Brand href={signedIn ? "/today" : "/"} size="lg" />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          {signedIn ? <LogoutButton /> : null}
        </div>
      </header>
      <main id="main" className="relative z-10 mx-auto w-full max-w-2xl flex-1 px-4 pt-4 pb-16 sm:px-6 sm:pt-8">
        {children}
      </main>
    </div>
  );
}
