import type { Metadata } from "next";
import { Fraunces, Inter, Source_Serif_4 } from "next/font/google";

import { ThemeProvider } from "@/components/theme/theme-provider";

import "./globals.css";

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"] });
const sourceSerif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"] });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "NewsHelper", template: "%s · NewsHelper" },
  description: "Your morning, on one page: a personal newspaper that learns what you care about.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fraunces.variable} ${sourceSerif.variable} ${inter.variable} h-full`}
    >
      <body className="flex min-h-full flex-col">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
