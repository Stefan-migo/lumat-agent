import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("renders a three-metric row with separators", () => {
    const { container } = render(
      <StatCard metrics={[
        { label: "Hoy", value: "$1.200" },
        { label: "Este mes", value: "$8.400" },
        { label: "Promedio", value: "$2.800" },
      ]} />,
    );

    expect(screen.getByText("Hoy")).toBeInTheDocument();
    expect(screen.getByText("$1.200")).toBeInTheDocument();
    expect(screen.getByText("Este mes")).toBeInTheDocument();
    expect(screen.getByText("$8.400")).toBeInTheDocument();
    expect(screen.getByText("Promedio")).toBeInTheDocument();
    expect(screen.getByText("$2.800")).toBeInTheDocument();
    expect(container.querySelectorAll(".stat-card__metric")).toHaveLength(3);
  });

  it("preserves the single-value card composition", () => {
    render(<StatCard label="Conversaciones" value={12} context="Hoy" />);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Conversaciones")).toBeInTheDocument();
  });
});
