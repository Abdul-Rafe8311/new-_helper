"use client";

import { Headphones, Menu } from "lucide-react";

import { Brand } from "@/components/brand/brand";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

import { AvatarMenu } from "./avatar-menu";
import { useChrome } from "./chrome-context";
import { DownloadButton } from "./download-button";

type MastheadProps = {
  displayName: string;
  email: string;
  pdfDate: string;
  /** Show the Listen placeholder (the audio briefing is not built yet). */
  listen?: boolean;
};

/** The wordmark on the left; the PDF action and the account control on the right. */
export function Masthead({ displayName, email, pdfDate, listen = false }: MastheadProps) {
  const { menuOpen, setMenuOpen } = useChrome();
  return (
    <header className="relative z-20 mx-auto flex h-16 w-full max-w-[1680px] items-center gap-1.5 px-4 sm:h-20 sm:gap-3 lg:h-[88px] lg:px-8">
      <Button
        variant="ghost"
        size="icon-sm"
        className="-ml-2 lg:hidden"
        aria-label="Open menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen(true)}
      >
        <Menu aria-hidden="true" />
      </Button>
      <Brand href="/today" className="text-lg min-[400px]:text-2xl sm:text-3xl" />
      <div className="ml-auto flex items-center gap-1 sm:gap-3">
        <DownloadButton defaultDate={pdfDate} />
        {listen ? (
          <Button
            variant="outline"
            disabled
            aria-label="Listen (coming soon)"
            className="size-9 rounded-full p-0 font-semibold sm:size-10 sm:w-auto sm:px-3 lg:px-4"
          >
            <Headphones aria-hidden="true" />
            <span className="hidden lg:inline">Listen (coming soon)</span>
          </Button>
        ) : null}
        <ThemeToggle />
        <AvatarMenu name={displayName} email={email} />
      </div>
    </header>
  );
}
