import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WhyChip } from "../why-chip";

const BREAKDOWN = {
  components: { semantic: 0.21, topic: 0.12, recency: 0.08 },
  penalties: { seen: 0.05 },
  total: 0.36,
  cluster_size: 4,
  terms: ["agents"],
};

describe("WhyChip", () => {
  it("is plain text when there is no breakdown", () => {
    render(<WhyChip reason="You follow cricket" />);
    expect(screen.getByText("You follow cricket")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("opens a score breakdown tooltip on click", () => {
    render(<WhyChip reason="You follow AI" breakdown={BREAKDOWN} />);
    expect(screen.queryByText("Score breakdown")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Why you're seeing this: You follow AI/ }));
    expect(screen.getByText("Score breakdown")).toBeInTheDocument();
    expect(screen.getByText("36/100")).toBeInTheDocument();
    expect(screen.getByText("Close to your interests")).toBeInTheDocument();
    expect(screen.getByText("Seen before")).toBeInTheDocument();
    expect(screen.getByText(/Covered by 4 outlets/)).toBeInTheDocument();
  });
});
