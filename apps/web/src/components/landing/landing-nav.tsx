import Link from "next/link";

/** Original multicolour emblem: four rounded petals, one per desk colour. */
function Emblem() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="9.5" height="9.5" rx="4" fill="#e8715a" />
      <rect x="12.5" y="2" width="9.5" height="9.5" rx="4" fill="#f2b544" />
      <rect x="2" y="12.5" width="9.5" height="9.5" rx="4" fill="#3fb5a8" />
      <rect x="12.5" y="12.5" width="9.5" height="9.5" rx="4" fill="#b79ced" />
    </svg>
  );
}

export function LandingNav() {
  return (
    <header className="lp-nav">
      <Link href="/" className="lp-brand" aria-label="NewsHelper home">
        <Emblem />
        NewsHelper
      </Link>
      <nav className="lp-center" aria-label="Page sections">
        <a href="#how-it-works">How it works</a>
        <a href="#read-your-way">Read your way</a>
      </nav>
      <div className="lp-right">
        <Link href="/login" className="lp-pill lp-pill--ghost lp-signin">
          Sign in
        </Link>
        <Link href="/signup" className="lp-pill lp-pill--light">
          Build my paper
        </Link>
      </div>
    </header>
  );
}
