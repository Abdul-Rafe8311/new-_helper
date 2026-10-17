import type { Metadata } from "next";
import Link from "next/link";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <>
      <h1 className="su-title">Good morning.</h1>
      <p className="su-sub">
        New here?<Link href="/signup">Create your paper</Link>
      </p>
      <LoginForm />
    </>
  );
}
