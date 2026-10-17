import type { Metadata } from "next";
import Link from "next/link";

import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = { title: "Start my paper" };

export default function SignupPage() {
  return (
    <>
      <h1 className="su-title">Create your paper</h1>
      <p className="su-sub">
        Already have an account?<Link href="/login">Sign in</Link>
      </p>
      <SignupForm />
    </>
  );
}
