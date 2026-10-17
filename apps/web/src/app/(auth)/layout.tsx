import Link from "next/link";

import { Rule } from "@/components/paper";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="font-display text-xl font-black tracking-tight">
          NewsHelper
        </Link>
        <ThemeToggle />
      </header>
      <main className="mx-auto w-full max-w-md flex-1 px-4 pt-6 pb-16 sm:pt-12">
        <Rule variant="thick" className="mb-6" />
        {children}
      </main>
    </div>
  );
}
