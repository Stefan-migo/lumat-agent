import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { StatusBadge, statusTone } from "./StatusBadge";
import type { Status } from "./StatusBadge";

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
    expect(screen.getByText("Atención humana")).toHaveAttribute("data-tone", "warning");
  });

  it("renders the approved Spanish label for every supported status (DS-UI-LABELS)", () => {
    const cases: Array<[Status, string]> = [
      ["bot", "Agente atendiendo"],
      ["human", "Atención humana"],
      ["closed", "Cerrada"],
      ["pending", "En espera"],
      ["escalated", "Escalado"],
    ];
    for (const [status, label] of cases) {
      const { unmount } = render(<StatusBadge status={status} />);
      expect(screen.getByText(label)).toHaveAttribute("data-tone", statusTone[status]);
      unmount();
    }
  });

  it("keeps status meaning in visible text, independent of decorative badge borders", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    const { unmount } = render(<StatusBadge status="escalated" />);
    const badge = screen.getByText("Escalado");
    expect(badge).toHaveAttribute("data-tone", "danger");
    expect(badge).toHaveTextContent("Escalado");
    expect(css).toMatch(/\.badge--danger\s*\{[^}]*border-color:\s*var\(--danger-border\)/s);
    unmount();
  });

  it("never renders the raw status value", () => {
    render(<StatusBadge status="human" />);
    expect(screen.queryByText("human")).not.toBeInTheDocument();
  });

  it("prefers an explicit label prop over the default map", () => {
    render(<StatusBadge status="closed" label="Resuelta" />);
    expect(screen.getByText("Resuelta")).toBeInTheDocument();
    expect(screen.queryByText("Cerrada")).not.toBeInTheDocument();
  });
});
