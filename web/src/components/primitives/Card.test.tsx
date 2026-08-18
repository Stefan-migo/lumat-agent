import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

describe("Card (T8.2)", () => {
  it("renders an optional title and its content", () => {
    render(<Card title="Client">Camila Soto</Card>);
    expect(screen.getByRole("heading", { name: "Client" })).toBeInTheDocument();
    expect(screen.getByText("Camila Soto")).toBeInTheDocument();
  });
});
