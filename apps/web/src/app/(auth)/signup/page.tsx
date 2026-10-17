import type { Metadata } from "next";
import Link from "next/link";

import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = { title: "Start my paper" };

export default function SignupPage() {
  return (
    <>
      <h1 className="page-title text-4xl sm:text-[2.6rem]">Create your paper</h1>
      <p className="lede mt-3 text-base">Two minutes now, and tomorrow&apos;s front page is about what you care about.</p>
      <p className="mt-3 mb-8 font-sans text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-ink underline underline-offset-4">
          Sign in
        </Link>
      </p>
      <SignupForm />
    </>
  );
}
