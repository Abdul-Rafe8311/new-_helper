"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={pending}
      onClick={() =>
        startTransition(async () => {
          await api.auth.logout().catch(() => undefined);
          router.push("/login");
          router.refresh();
        })
      }
    >
      <LogOut aria-hidden="true" />
      <span className="sr-only sm:not-sr-only">Sign out</span>
    </Button>
  );
}
