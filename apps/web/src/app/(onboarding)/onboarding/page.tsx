import type { Metadata } from "next";

import { Placeholder } from "@/components/shell/placeholder";

export const metadata: Metadata = { title: "Set up your paper" };

export default function OnboardingPage() {
  return (
    <Placeholder title="Set up your paper">
      <p>A few quick questions about what you like to read will go here.</p>
    </Placeholder>
  );
}
