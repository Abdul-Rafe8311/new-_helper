import Link from "next/link";

import { cn } from "@/lib/utils";

const SIZES = {
  md: "text-2xl",
  lg: "text-3xl",
  sm: "text-xl",
} as const;

/**
 * The NewsHelper wordmark: Fraunces Black with a coloured full stop. The stop takes `--cat`, so it
 * follows the reader's category inside the app and is brand blue everywhere else (see `.brand-scope`).
 */
export function Brand({
  href = "/",
  size = "md",
  className,
}: {
  href?: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <Link
      href={href}
      aria-label="NewsHelper home"
      className={cn(
        "inline-flex min-h-11 items-center rounded-md font-display font-black tracking-tight text-ink outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
        SIZES[size],
        className,
      )}
    >
      NewsHelper
      <span aria-hidden="true" className="text-cat">
        .
      </span>
    </Link>
  );
}
