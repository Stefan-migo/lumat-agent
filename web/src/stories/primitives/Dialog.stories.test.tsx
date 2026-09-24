import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DialogConfirmView } from "./Dialog.stories";

describe("Dialog confirmation story fixture", () => {
  it("uses Button primitives for actions and contains no inline styles", () => {
    const { container } = render(<DialogConfirmView />);

    expect(screen.getByRole("button", { name: "Eliminar registro" })).toHaveClass(
      "btn",
      "btn--secondary",
    );
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveClass("btn--secondary");
    expect(screen.getByRole("button", { name: "Eliminar" })).toHaveClass("btn--primary");
    expect(container.querySelectorAll("[style]")).toHaveLength(0);
  });
});
