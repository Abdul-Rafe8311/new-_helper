import type { ReactNode } from "react";

import type { Session } from "@/lib/server/session";

import { paperNameFor } from "@/components/shell/app-header";

import { ChromeProvider } from "./chrome-context";
import { Sidebar } from "./sidebar";
import { Toolbar } from "./toolbar";

/** The signed-in frame: icon rail (tab bar on phones), toolbar, and the page below it. */
export function ReaderChrome({ session, children }: { session: Session; children: ReactNode }) {
  return (
    <ChromeProvider>
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col pb-14 md:pb-0 md:pl-[60px]">
        <Toolbar
          paperName={paperNameFor(session)}
          displayName={session.user.display_name}
          email={session.user.email}
        />
        {children}
      </div>
    </ChromeProvider>
  );
}

export function ReaderChromeSkeleton() {
  return (
    <div aria-hidden="true" className="flex min-h-screen flex-1 flex-col md:pl-[60px]">
      <div className="flex items-center gap-3 border-b border-rule px-4 py-3">
        <div className="size-8 animate-pulse bg-paper-2" />
        <div className="h-6 w-40 animate-pulse bg-paper-2" />
        <div className="ml-4 hidden h-8 flex-1 animate-pulse bg-paper-2 sm:block sm:max-w-md" />
      </div>
    </div>
  );
}
