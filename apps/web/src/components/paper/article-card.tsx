import Image from "next/image";

import { cn } from "@/lib/utils";

import { Byline } from "./byline";
import type { CardArticle, CardVariant } from "./types";
import { WhyChip } from "./why-chip";

type ArticleCardProps = {
  article: CardArticle;
  variant?: CardVariant;
  className?: string;
};

const headlineSize: Record<CardVariant, string> = {
  lead: "text-3xl sm:text-5xl font-black leading-[1.05]",
  feature: "text-2xl sm:text-3xl font-bold leading-tight",
  standard: "text-xl font-bold leading-snug",
  brief: "text-base font-semibold leading-snug",
  explore: "text-xl font-bold leading-snug",
};

function Picture({ article, variant }: { article: CardArticle; variant: CardVariant }) {
  const ratio = variant === "lead" ? "aspect-[16/9]" : "aspect-[3/2]";
  return (
    <figure className={cn("relative mb-3 overflow-hidden bg-paper-2", ratio)}>
      {article.imageUrl ? (
        <Image
          src={article.imageUrl}
          alt=""
          fill
          unoptimized
          sizes="(min-width: 768px) 50vw, 100vw"
          className="object-cover grayscale-[15%]"
        />
      ) : (
        <div aria-hidden="true" className="halftone absolute inset-0" />
      )}
    </figure>
  );
}

/** One story, in one of five layouts: lead, feature, standard, brief or explore. */
export function ArticleCard({ article, variant = "standard", className }: ArticleCardProps) {
  const showPicture = variant === "lead" || (variant === "feature" && Boolean(article.imageUrl));
  const showSummary = variant !== "brief" && Boolean(article.summary);

  return (
    <article
      data-variant={variant}
      className={cn(
        "group flex flex-col",
        variant === "explore" && "border border-dashed border-accent/60 p-4",
        variant === "brief" && "border-b border-rule pb-3",
        className,
      )}
    >
      {variant === "explore" ? <p className="kicker mb-2 text-accent">Off your beat</p> : null}
      {variant !== "explore" && article.section && variant !== "brief" ? (
        <p className="kicker mb-1.5 text-accent">{article.section}</p>
      ) : null}
      {showPicture ? <Picture article={article} variant={variant} /> : null}
      <h3 className={cn("font-display text-ink", headlineSize[variant])}>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="decoration-accent decoration-2 underline-offset-4 hover:underline focus-visible:underline focus-visible:outline-none"
        >
          {article.headline}
        </a>
      </h3>
      {showSummary ? (
        <p
          className={cn(
            "mt-2 font-serif text-ink/90",
            variant === "lead" ? "text-lg leading-relaxed" : "text-[0.95rem] leading-relaxed",
            variant === "standard" && "line-clamp-4",
          )}
        >
          {article.summary}
        </p>
      ) : null}
      <Byline
        className="mt-2"
        source={article.source}
        author={variant === "brief" ? undefined : article.author}
        publishedAt={variant === "brief" ? undefined : article.publishedAt}
        readingMinutes={article.readingMinutes}
      />
      {article.why && variant !== "brief" ? <WhyChip className="mt-2 self-start" reason={article.why} /> : null}
    </article>
  );
}
