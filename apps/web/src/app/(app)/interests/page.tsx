import type { Metadata } from "next";

import { Placeholder } from "@/components/shell/placeholder";

export const metadata: Metadata = { title: "Interests" };

export default function InterestsPage() {
  return (
    <Placeholder title="Your interests">
      <p>See and tune what your paper has learned about you: topics, people, places and sources.</p>
    </Placeholder>
  );
}
