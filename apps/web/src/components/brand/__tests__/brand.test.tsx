import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Brand } from "../brand";

describe("Brand", () => {
  it("is one link home with a decorative full stop", () => {
    render(<Brand />);
    const link = screen.getByRole("link", { name: "NewsHelper home" });
    expect(link).toHaveAttribute("href", "/");
    expect(link).toHaveTextContent("NewsHelper.");
    expect(link.querySelector("span")).toHaveAttribute("aria-hidden", "true");
  });

  it("can point somewhere else, e.g. today's paper for a signed-in reader", () => {
    render(<Brand href="/today" />);
    expect(screen.getByRole("link", { name: "NewsHelper home" })).toHaveAttribute("href", "/today");
  });
});
