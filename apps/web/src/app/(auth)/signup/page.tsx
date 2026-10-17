import type { Metadata } from "next";

import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = { title: "Start my paper" };

export default function SignupPage() {
  return (
    <>
      <h1 className="font-display text-4xl font-black">Start your paper.</h1>
      <p className="mt-2 mb-8 font-serif text-muted">
        Two minutes now, and tomorrow&apos;s front page is about the things you care about.
      </p>
      <SignupForm />
    </>
  );
}
