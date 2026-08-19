import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginDefault, LoginError } from "./Login.stories";

describe("Login page story (T5.4, R-PRD-PG-6)", () => {
  it("renders the centered 'Lumat Panel' auth card", () => {
    const { container } = render(<LoginDefault />);
    expect(screen.getByRole("heading", { name: "Lumat Panel" })).toBeInTheDocument();
    // .card is the auth card (matches Jinja login.html .card max-width 24rem).
    const card = screen.getByRole("heading", { name: "Lumat Panel" }).closest(".card") as HTMLElement;
    expect(card).not.toBeNull();
    expect(container.querySelector(".card")).not.toBeNull();
  });

  it("renders username + password + Login button", () => {
    render(<LoginDefault />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    const password = screen.getByLabelText(/password/i) as HTMLInputElement;
    expect(password.type).toBe("password");
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("does not render an error message in the default state", () => {
    render(<LoginDefault />);
    expect(screen.queryByText(/invalid credentials/i)).not.toBeInTheDocument();
  });
});

describe("Login Error story", () => {
  it("renders the auth card with an error message", () => {
    render(<LoginError />);
    expect(screen.getByRole("heading", { name: "Lumat Panel" })).toBeInTheDocument();
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });
});
