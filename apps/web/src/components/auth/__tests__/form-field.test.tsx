import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormField } from "../form-field";

describe("FormField", () => {
  it("links its hint, and swaps the hint for the error when there is one", () => {
    const { rerender } = render(<FormField id="email" label="Email" hint="Use your work address." />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-describedby", "email-hint");
    rerender(<FormField id="email" label="Email" hint="Use your work address." error="Enter a valid email." />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-describedby", "email-error");
    expect(screen.queryByText("Use your work address.")).not.toBeInTheDocument();
  });

  it("lets a password be shown and hidden without losing what was typed", () => {
    render(<FormField id="password" label="Password" type="password" />);
    const input = screen.getByLabelText("Password");
    fireEvent.change(input, { target: { value: "hunter2hunter2" } });
    fireEvent.click(screen.getByRole("button", { name: "Show characters" }));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("hunter2hunter2");
    fireEvent.click(screen.getByRole("button", { name: "Hide characters" }));
    expect(input).toHaveAttribute("type", "password");
  });
});
