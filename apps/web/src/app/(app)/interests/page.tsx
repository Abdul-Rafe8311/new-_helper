import type { Metadata } from "next";
import { Suspense } from "react";

import { InterestsWorkspace } from "@/components/reader/interests-workspace";
import { PageFrame } from "@/components/reader/page-frame";
import { ReaderSkeleton } from "@/components/reader/skeletons";
import { SideNav } from "@/components/reader/side-nav";
import { serverApi } from "@/lib/server/session";

export const metadata: Metadata = { title: "Interests" };

export default function InterestsPage() {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Interests />
    </Suspense>
  );
}

async function Interests() {
  const api = await serverApi();
  const [interests, timeline] = await Promise.all([api.interests.get(), api.interests.timeline()]);
  return (
    <PageFrame nav={<SideNav base="/today" />}>
      <InterestsWorkspace initial={interests} initialTimeline={timeline} />
    </PageFrame>
  );
}
