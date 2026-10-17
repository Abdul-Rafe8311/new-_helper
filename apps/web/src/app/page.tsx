export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-6 px-6 text-center">
      <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Your morning, on one page</p>
      <h1 className="font-serif text-5xl font-bold tracking-tight sm:text-6xl">NewsHelper</h1>
      <p className="max-w-xl text-lg text-zinc-600 dark:text-zinc-400">
        A personal morning newspaper that learns what you care about, gathers the day&apos;s
        stories from across the web, and prints one paper made just for you.
      </p>
      <p className="text-sm text-zinc-500">Coming soon.</p>
    </main>
  );
}
