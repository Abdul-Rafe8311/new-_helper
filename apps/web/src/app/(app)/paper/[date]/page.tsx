import type { Metadata } from "next";
import { Suspense } from "react";

import { EditionPage } from "@/components/reader/edition-page";
import { ReaderSkeleton } from "@/components/reader/skeletons";

export const metadata: Metadata = { title: "Past edition" };

export default function PaperPage({ params }: PageProps<"/paper/[date]">) {
  return (
    <Suspense fallback={<ReaderSkeleton />}>
      <Edition params={params} />
    </Suspense>
  );
}

async function Edition({ params }: Pick<PageProps<"/paper/[date]">, "params">) {
  const { date } = await params;
  return <EditionPage date={date} basePath={`/paper/${date}`} />;
}
