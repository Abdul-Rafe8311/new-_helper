import type { Metadata } from "next";
import Link from "next/link";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <>
      <h1 className="page-title text-4xl sm:text-[2.6rem]">Good morning.</h1>
      <p className="lede mt-3 text-base">Sign in to read today&apos;s paper.</p>
      <p className="mt-3 mb-8 font-sans text-sm text-muted">
        New here?{" "}
        <Link href="/signup" className="font-semibold text-ink underline underline-offset-4">
          Create your paper
        </Link>
      </p>
      <LoginForm />
    </>
  );
}
