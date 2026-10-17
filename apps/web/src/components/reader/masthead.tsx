"use client";

import { Menu } from "lucide-react";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

import { AvatarMenu } from "./avatar-menu";
import { useChrome } from "./chrome-context";
import { DownloadButton } from "./download-button";

type MastheadProps = { displayName: string; email: string; pdfDate: string };

/** The wordmark on the left; the PDF action and the account control on the right. */
export function Masthead({ displayName, email, pdfDate }: MastheadProps) {
  const { menuOpen, setMenuOpen } = useChrome();
  return (
    <header className="relative z-20 mx-auto flex h-16 w-full max-w-[1680px] items-center gap-3 px-4 sm:h-20 lg:h-[88px] lg:px-8">
      <Button
        variant="ghost"
        size="icon"
        className="-ml-2 lg:hidden"
        aria-label="Open menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen(true)}
      >
        <Menu aria-hidden="true" />
      </Button>
      <Link href="/today" className="font-display text-2xl font-black tracking-tight text-ink sm:text-3xl">
        NewsHelper<span aria-hidden="true" className="text-cat">.</span>
      </Link>
      <div className="ml-auto flex items-center gap-1.5 sm:gap-3">
        <DownloadButton defaultDate={pdfDate} />
        <ThemeToggle />
        <AvatarMenu name={displayName} email={email} />
      </div>
    </header>
  );
}
