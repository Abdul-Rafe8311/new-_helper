import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ApiError } from "@/lib/api";
import { PageFrame } from "@/components/reader/page-frame";
import { SideNav } from "@/components/reader/side-nav";
import { StoryDetail } from "@/components/reader/story-detail";
import { serverApi } from "@/lib/server/session";

export const metadata: Metadata = { title: "Story" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function StoryPage({ params }: PageProps<"/story/[id]">) {
  return (
    <Suspense
      fallback={
        <PageFrame nav={<SideNav base="/today" />}>
          <div aria-busy="true" role="status" aria-label="Loading story" className="grid gap-10 py-10 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="h-4 w-56 animate-pulse rounded bg-paper-2" />
              <div className="h-14 w-full animate-pulse rounded bg-paper-2" />
              <div className="h-14 w-3/4 animate-pulse rounded bg-paper-2" />
            </div>
            <div className="aspect-[5/4] animate-pulse rounded-2xl bg-paper-2" />
          </div>
        </PageFrame>
      }
    >
      <Story params={params} />
    </Suspense>
  );
}

async function Story({ params }: Pick<PageProps<"/story/[id]">, "params">) {
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  const api = await serverApi();
  const story = await api.story(id).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return <StoryDetail story={story} now={new Date().toISOString()} />;
}
