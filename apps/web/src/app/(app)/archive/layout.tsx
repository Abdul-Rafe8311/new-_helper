import { Suspense, type ReactNode } from "react";

import { ArchiveWorkspace } from "@/components/reader/archive-workspace";
import { ARCHIVE_PAGE } from "@/components/reader/model";
import { ReaderSkeleton } from "@/components/reader/skeletons";
import { serverApi } from "@/lib/server/session";

export default function ArchiveLayout({ children }: LayoutProps<"/archive">) {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Shell>{children}</Shell>
    </Suspense>
  );
}

async function Shell({ children }: { children: ReactNode }) {
  const api = await serverApi();
  const first = await api.editions.list({ limit: ARCHIVE_PAGE });
  return <ArchiveWorkspace initial={first}>{children}</ArchiveWorkspace>;
}
