"use client";

import { LogOut, Settings, SlidersHorizontal } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

const ITEM =
  "flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 font-sans text-sm outline-none data-[highlighted]:bg-paper-2 [&_svg]:size-4 [&_svg]:text-muted";

export function initialsOf(name: string): string {
  const letters = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "");
  return letters.join("") || "?";
}

/** The reader's avatar; opens a small menu with their links and sign out. */
export function AvatarMenu({ name, email }: { name: string; email: string }) {
  const router = useRouter();

  async function logout() {
    await api.auth.logout().catch(() => undefined);
    router.push("/login");
    router.refresh();
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={`${initialsOf(name)}: account menu for ${name}`}
        className="inline-flex size-8 items-center justify-center rounded-full bg-ink font-sans text-xs font-semibold text-paper outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {initialsOf(name)}
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-52 rounded-md border border-rule bg-paper p-1 text-ink shadow-lg"
        >
          <DropdownMenu.Label className="px-2 py-1.5">
            <span className="block font-sans text-sm font-semibold">{name}</span>
            <span className="block font-sans text-xs text-muted">{email}</span>
          </DropdownMenu.Label>
          <DropdownMenu.Separator className="my-1 h-px bg-rule" />
          <DropdownMenu.Item className={ITEM} onSelect={() => router.push("/interests")}>
            <SlidersHorizontal aria-hidden="true" /> Interests
          </DropdownMenu.Item>
          <DropdownMenu.Item className={ITEM} onSelect={() => router.push("/settings")}>
            <Settings aria-hidden="true" /> Settings
          </DropdownMenu.Item>
          <DropdownMenu.Separator className="my-1 h-px bg-rule" />
          <DropdownMenu.Item className={ITEM} onSelect={() => void logout()}>
            <LogOut aria-hidden="true" /> Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
