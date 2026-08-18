import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Avatar } from "./Avatar";

describe("Avatar (T8.5)", () => {
  it("uses initials when no image source is provided", () => {
    render(<Avatar name="Camila Soto" />);
    expect(screen.getByText("CS")).toBeInTheDocument();
  });

  it("renders the named image when a source is provided", () => {
    render(<Avatar name="Camila Soto" src="/camila.png" />);
    expect(screen.getByRole("img", { name: "Camila Soto" })).toHaveAttribute(
      "src",
      "/camila.png",
    );
  });
});
