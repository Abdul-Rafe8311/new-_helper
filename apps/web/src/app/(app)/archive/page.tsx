import type { Metadata } from "next";
import { Suspense } from "react";

import { ArchiveList } from "@/components/reader/archive-list";
import { ARCHIVE_PAGE } from "@/components/reader/model";
import { ReaderSkeleton } from "@/components/reader/skeletons";
import { serverApi } from "@/lib/server/session";

export const metadata: Metadata = { title: "Archive" };

export default function ArchivePage() {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Archive />
    </Suspense>
  );
}

async function Archive() {
  const api = await serverApi();
  const first = await api.editions.list({ limit: ARCHIVE_PAGE });
  return <ArchiveList initial={first} />;
}
