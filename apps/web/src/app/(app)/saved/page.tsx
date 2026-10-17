import type { Metadata } from "next";
import { Suspense } from "react";

import { ReaderSkeleton } from "@/components/reader/skeletons";
import { SavedWorkspace } from "@/components/reader/saved-workspace";
import { serverApi } from "@/lib/server/session";

export const metadata: Metadata = { title: "Saved" };

export default function SavedPage() {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Saved />
    </Suspense>
  );
}

async function Saved() {
  const api = await serverApi();
  const items = await api.saved();
  return <SavedWorkspace items={items} now={new Date().toISOString()} />;
}
