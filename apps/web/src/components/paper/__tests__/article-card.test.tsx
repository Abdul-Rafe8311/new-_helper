import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ArticleCard } from "../article-card";
import { MOCK_ARTICLES } from "../mock";
import type { CardVariant } from "../types";

const VARIANTS: CardVariant[] = ["lead", "feature", "standard", "brief", "explore"];

describe("ArticleCard", () => {
  it.each(VARIANTS)("renders the %s variant with a link to the original", (variant) => {
    const article = MOCK_ARTICLES[variant];
    render(<ArticleCard variant={variant} article={article} />);

    const card = screen.getByRole("article");
    expect(card).toHaveAttribute("data-variant", variant);
    const link = screen.getByRole("link", { name: article.headline });
    expect(link).toHaveAttribute("href", article.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(screen.getByText(article.source)).toBeInTheDocument();
  });

  it("shows summary, byline details and the why chip on a lead story", () => {
    const article = MOCK_ARTICLES.lead;
    render(<ArticleCard variant="lead" article={article} />);

    expect(screen.getByText(article.summary!)).toBeInTheDocument();
    expect(screen.getByText(`By ${article.author}`)).toBeInTheDocument();
    expect(screen.getByText("6 min read")).toBeInTheDocument();
    expect(screen.getByText("17 Oct")).toHaveAttribute("dateTime", article.publishedAt);
    expect(screen.getByText(article.why!)).toBeInTheDocument();
    expect(screen.getByText("World")).toBeInTheDocument();
  });

  it("keeps briefs to a headline and source", () => {
    const article = { ...MOCK_ARTICLES.standard, id: "x" };
    render(<ArticleCard variant="brief" article={article} />);

    expect(screen.queryByText(article.summary!)).not.toBeInTheDocument();
    expect(screen.queryByText(article.why!)).not.toBeInTheDocument();
    expect(screen.queryByText(article.section!)).not.toBeInTheDocument();
  });

  it("labels explore stories as off the reader's beat", () => {
    render(<ArticleCard variant="explore" article={MOCK_ARTICLES.explore} />);
    expect(screen.getByText("Off your beat")).toBeInTheDocument();
  });
});
