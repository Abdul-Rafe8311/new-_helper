import type { Metadata } from "next";

import { Placeholder } from "@/components/shell/placeholder";

export const metadata: Metadata = { title: "Archive" };

export default function ArchivePage() {
  return (
    <Placeholder title="Archive">
      <p>Past editions will be filed here, one per morning, each with its PDF.</p>
    </Placeholder>
  );
}
