import type { Metadata } from "next";

import { PageFrame } from "@/components/reader/page-frame";
import { SideNav } from "@/components/reader/side-nav";
import { Placeholder } from "@/components/shell/placeholder";

export const metadata: Metadata = { title: "Interests" };

export default function InterestsPage() {
  return (
    <PageFrame nav={<SideNav base="/today" />}>
      <Placeholder title="Your interests">
        <p>See and tune what your paper has learned about you: topics, people, places and sources.</p>
      </Placeholder>
    </PageFrame>
  );
}
