"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { Dialog } from "radix-ui";
import { useState, type ReactNode } from "react";

import { DemoButton } from "@/components/auth/demo-button";

import { SAMPLE_SECTIONS } from "./sample-edition";

const FOCUS = "outline-none focus-visible:ring-[3px] focus-visible:ring-[#FEE951]/70";
const TOUCH = "inline-flex min-h-11 items-center justify-center rounded-full px-4 text-sm font-semibold";

function SectionList({ onNavigate }: { onNavigate?: () => void }) {
  const items = [{ slug: "sample-edition", label: "Today" }, ...SAMPLE_SECTIONS.map(({ slug, label }) => ({ slug: `story-${slug}`, label }))];
  return (
    <nav aria-label="Sections">
      <ul className="space-y-1">
        {items.map(({ slug, label }) => (
          <li key={slug}>
            <a
              href={`#${slug}`}
              onClick={onNavigate}
              className={`flex min-h-11 items-center rounded-full px-4 text-[17px] font-semibold text-[#d9d3c0] hover:bg-white/5 hover:text-[#f4edda] ${FOCUS}`}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Top bar, the desktop section sidebar and the mobile drawer. The page content is the children. */
export function LandingShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#1d1d1b]/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1360px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
          <div className="flex items-center gap-1">
            <Dialog.Root open={open} onOpenChange={setOpen}>
              <Dialog.Trigger
                aria-label="Open sections menu"
                className={`inline-flex size-11 items-center justify-center rounded-full text-[#f4edda] hover:bg-white/5 lg:hidden ${FOCUS}`}
              >
                <Menu aria-hidden="true" className="size-5" />
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 lg:hidden" />
                <Dialog.Content
                  aria-describedby={undefined}
                  className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] overflow-y-auto bg-[#1d1d1b] p-5 shadow-2xl outline-none lg:hidden"
                >
                  <div className="mb-5 flex items-center justify-between">
                    <Dialog.Title className="font-[family-name:var(--font-figtree)] text-xl font-extrabold text-[#f4edda]">
                      NewsHelper
                    </Dialog.Title>
                    <Dialog.Close
                      aria-label="Close menu"
                      className={`inline-flex size-11 items-center justify-center rounded-full text-[#f4edda] hover:bg-white/5 ${FOCUS}`}
                    >
                      <X aria-hidden="true" className="size-5" />
                    </Dialog.Close>
                  </div>
                  <SectionList onNavigate={() => setOpen(false)} />
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            <Link
              href="/"
              className={`inline-flex min-h-11 items-center rounded-full px-2 font-[family-name:var(--font-figtree)] text-2xl font-extrabold tracking-tight text-[#f4edda] ${FOCUS}`}
            >
              NewsHelper
            </Link>
          </div>
          <div className="flex flex-wrap items-center gap-1 sm:gap-2">
            <Link href="/login" className={`${TOUCH} text-[#f4edda] hover:bg-white/5 ${FOCUS}`}>
              Sign in
            </Link>
            <DemoButton buttonClassName={`${TOUCH} h-auto border border-[#a8b89a]/60 bg-transparent text-[#f4edda] hover:bg-white/5 ${FOCUS}`} />
            <Link href="/signup" className={`${TOUCH} bg-[#FEE951] text-[#1d1d1b] hover:brightness-95 ${FOCUS}`}>
              Start my paper
            </Link>
          </div>
        </div>
      </header>
      <div className="mx-auto flex w-full max-w-[1360px] gap-8 px-4 sm:px-6">
        <aside className="sticky top-20 hidden max-h-[calc(100vh-6rem)] w-56 shrink-0 self-start overflow-y-auto py-8 lg:block">
          <SectionList />
        </aside>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </>
  );
}
