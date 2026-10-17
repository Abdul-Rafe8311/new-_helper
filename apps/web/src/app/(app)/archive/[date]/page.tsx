import type { Metadata } from "next";
import { Suspense } from "react";

import { EditionPage } from "@/components/reader/edition-page";
import { ReaderSkeleton } from "@/components/reader/skeletons";

export const metadata: Metadata = { title: "Archive" };

export default function ArchiveEditionPage({ params }: PageProps<"/archive/[date]">) {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Edition params={params} />
    </Suspense>
  );
}

async function Edition({ params }: Pick<PageProps<"/archive/[date]">, "params">) {
  const { date } = await params;
  return <EditionPage date={date} basePath={`/archive/${date}`} />;
}
