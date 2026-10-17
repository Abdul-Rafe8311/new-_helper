import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Home from "../page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

describe("Home page", () => {
  it("renders one h1, the sample edition, how-it-works and the top-bar actions", () => {
    render(<Home />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Your morning, on one page" })).toBeInTheDocument();
    expect(screen.getByText("Sample edition")).toBeInTheDocument();
    const how = screen.getByRole("region", { name: "How it works" });
    expect(within(how).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Start my paper" })).toHaveAttribute("href", "/signup");
    expect(screen.getAllByRole("link", { name: "Sign in" })[0]).toHaveAttribute("href", "/login");
    expect(screen.getByRole("button", { name: "Try the demo" })).toBeEnabled();
  });
});
