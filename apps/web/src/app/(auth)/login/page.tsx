import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <>
      <h1 className="font-display text-4xl font-black">Good morning.</h1>
      <p className="mt-2 mb-8 font-serif text-muted">Sign in to read today&apos;s paper.</p>
      <LoginForm />
    </>
  );
}
