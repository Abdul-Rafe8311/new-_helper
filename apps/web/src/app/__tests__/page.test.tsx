import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import Home from "../page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

beforeAll(() => {
  window.matchMedia ??= ((query: string) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
  window.IntersectionObserver ??= class {
    constructor(readonly callback: IntersectionObserverCallback) {}
    observe = vi.fn();
    disconnect = vi.fn();
    unobserve = vi.fn();
  } as unknown as typeof IntersectionObserver;
});

describe("Home page", () => {
  it("has one h1, three sections and the real calls to action", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Your world. One daily paper.");
    expect(screen.getByRole("region", { name: "How it works" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Read your way" })).toBeInTheDocument();
    expect(document.querySelectorAll("main > * section, main section")).toHaveLength(3);
    expect(screen.getAllByRole("link", { name: "Build my paper" })[0]).toHaveAttribute("href", "/signup");
    expect(screen.getByRole("link", { name: "Open my paper" })).toHaveAttribute("href", "/today");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("names every topic desk and keeps the manifesto as one readable paragraph", () => {
    render(<Home />);
    expect(screen.getByRole("button", { name: "Science desk" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Technology desk" })).toBeInTheDocument();
    expect(screen.getAllByRole("button").filter((b) => /desk$/.test(b.getAttribute("aria-label") ?? ""))).toHaveLength(16);
    expect(screen.getByText(/NewsHelper brings the stories you care about/)).toBeInTheDocument();
  });
});
