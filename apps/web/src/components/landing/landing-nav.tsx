import Link from "next/link";

import { Brand } from "@/components/brand/brand";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function LandingNav() {
  return (
    <header className="lp-nav">
      <Brand size="md" className="justify-self-start text-xl sm:text-2xl" />
      <nav className="lp-center" aria-label="Page sections">
        <a href="#how-it-works">How it works</a>
        <a href="#read-your-way">Read your way</a>
      </nav>
      <div className="lp-right">
        <ThemeToggle />
        <Link href="/login" className="lp-pill lp-pill--ghost lp-signin">
          Sign in
        </Link>
        <Link href="/signup" aria-label="Build my paper" className="lp-pill lp-pill--primary max-sm:px-4">
          <span className="sm:hidden">Get started</span>
          <span className="hidden sm:inline">Build my paper</span>
        </Link>
      </div>
    </header>
  );
}
