import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

/** A calm "nothing here yet" panel: an icon, one line of what, one line of why, and an optional way forward. */
export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: { href: string; label: string };
}) {
  return (
    <div className="card mx-auto my-10 flex max-w-md flex-col items-center gap-2 px-6 py-12 text-center font-sans">
      <span className="mb-2 inline-flex size-12 items-center justify-center rounded-full bg-cat/10 text-cat">
        <Icon aria-hidden="true" className="size-6" />
      </span>
      <p className="text-xl font-extrabold tracking-tight">{title}</p>
      <p className="text-base text-muted">{body}</p>
      {action ? (
        <Button asChild variant="outline" className="mt-3">
          <Link href={action.href}>{action.label}</Link>
        </Button>
      ) : null}
    </div>
  );
}
