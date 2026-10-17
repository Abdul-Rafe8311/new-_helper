import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Masthead } from "../masthead";

describe("Masthead", () => {
  it("shows the paper name, edition number and date line in the reader's time zone", () => {
    // 20:30 UTC on the 16th is already the 17th in Karachi (UTC+5).
    render(
      <Masthead paperName="The Morning Ledger" date="2026-10-16T20:30:00Z" editionNumber={12} timeZone="Asia/Karachi" />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "The Morning Ledger" })).toBeInTheDocument();
    expect(screen.getByText("No. 12")).toBeInTheDocument();
    expect(screen.getByText("Saturday, 17 October 2026")).toBeInTheDocument();
  });

  it("fills the weather slot and falls back to 'First edition'", () => {
    const { container } = render(
      <Masthead paperName="Daily" date="2026-10-17T03:00:00Z" weather={<span>Lahore 24°C</span>} />,
    );

    expect(screen.getByText("First edition")).toBeInTheDocument();
    expect(container.querySelector('[data-slot="weather"]')).toHaveTextContent("Lahore 24°C");
  });
});
