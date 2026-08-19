import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge (T8.3)", () => {
  it("exposes its label and semantic tone", () => {
    render(<Badge tone="danger">Escalated</Badge>);
    expect(screen.getByText("Escalated")).toHaveAttribute(
      "data-tone",
      "danger",
    );
  });
});
