import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge, statusTone } from "./StatusBadge";

describe("StatusBadge (T8.4)", () => {
  it("maps every specified status to its design tone", () => {
    expect(statusTone).toEqual({
      bot: "neutral",
      human: "warning",
      closed: "success",
      pending: "warning",
      escalated: "danger",
    });
  });

  it("renders the supplied status as a readable badge", () => {
    render(<StatusBadge status="human" />);
    expect(screen.getByText("human")).toHaveAttribute("data-tone", "warning");
  });
});
