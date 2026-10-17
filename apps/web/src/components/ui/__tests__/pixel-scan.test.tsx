import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PixelScan } from "../pixel-scan";

describe("PixelScan", () => {
  it("renders one decorative canvas and survives an environment without 2D canvas support", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const { container, unmount } = render(<PixelScan label="CHOOSING" progress={0.4} />);
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveAttribute("aria-hidden", "true");
    expect(canvas).toHaveClass("pointer-events-none");
    unmount();
  });
});
