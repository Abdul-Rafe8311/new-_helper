import type { Metadata } from "next";
import { Suspense } from "react";

import { EditionPage } from "@/components/reader/edition-page";
import { ReaderSkeleton } from "@/components/reader/skeletons";

export const metadata: Metadata = { title: "Today" };

export default function TodayPage() {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <EditionPage date="today" basePath="/today" />
    </Suspense>
  );
}
