import type { Metadata } from "next";

import { ArchiveEmpty } from "@/components/reader/archive-workspace";

export const metadata: Metadata = { title: "Archive" };

export default function ArchivePage() {
  return <ArchiveEmpty />;
}
