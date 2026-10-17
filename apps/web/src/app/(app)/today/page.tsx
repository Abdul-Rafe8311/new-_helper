import type { Metadata } from "next";

import { Placeholder } from "@/components/shell/placeholder";

export const metadata: Metadata = { title: "Today" };

export default function TodayPage() {
  return (
    <Placeholder title="Today's paper">
      <p>Your first edition is on the press. Stories will appear here each morning.</p>
    </Placeholder>
  );
}
