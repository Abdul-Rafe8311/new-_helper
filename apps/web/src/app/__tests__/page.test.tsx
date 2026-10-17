import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Home from "../page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

describe("Home page", () => {
  it("renders the masthead, how-it-works and both calls to action", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1, name: "NewsHelper" })).toBeInTheDocument();
    expect(screen.getByText("Your morning, on one page")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Start my paper" })).toHaveAttribute("href", "/signup");
    expect(screen.getByRole("button", { name: "Try the demo" })).toBeEnabled();
  });
});
