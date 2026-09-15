import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { Skeleton } from "./Skeleton";

describe("Skeleton (2C-1)", () => {
  it("is decorative and accepts caller-controlled dimensions", () => {
    const { container } = render(<Skeleton width="12rem" height={24} />);
    const skeleton = container.querySelector(".skeleton");

    expect(skeleton).toHaveAttribute("aria-hidden", "true");
    expect(skeleton).toHaveStyle({ width: "12rem", height: "24px" });
  });

  it("does not require dimensions", () => {
    const { container } = render(<Skeleton />);
    expect(container.querySelector(".skeleton")).toBeInTheDocument();
  });
});
