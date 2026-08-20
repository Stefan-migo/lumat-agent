import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginAuth, LoginDefault, LoginError, LoginLoading } from "./Login.stories";

describe("Login default (T5.4, R-PRD-PG-1)", () => {
  it("renders the Lumat typographic lockup (Lumat + Panel operativo)", () => {
    const { container } = render(<LoginDefault />);
    expect(screen.getByText("Lumat")).toBeInTheDocument();
    expect(screen.getByText("Panel operativo")).toBeInTheDocument();
    // The lockup is typographic (no logo asset) — renders as brand text.
    expect(container.querySelector(".login-brand")).not.toBeNull();
  });

  it("renders Usuario + Contraseña + Iniciar sesión (Spanish auth)", () => {
    render(<LoginDefault />);
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    const password = screen.getByLabelText(/contraseña/i) as HTMLInputElement;
    expect(password.type).toBe("password");
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("does not render an error message in the default state", () => {
    render(<LoginDefault />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders a loading state that disables the submit action", () => {
    render(<LoginLoading />);
    expect(screen.getByText(/iniciando sesión/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeDisabled();
    // The form fields stay editable so a refresh does not clear a typed username.
    expect(screen.getByLabelText(/usuario/i)).toBeEnabled();
  });
});

describe("Login error (DS-UI-LOGIN)", () => {
  it("shows a generic non-destructive error that preserves the username", () => {
    // A failed attempt with a valid username "marcela" — the inline error
    // must keep the username value so the user can retry without retyping.
    render(<LoginAuth error="Credenciales inválidas" username="marcela" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Credenciales inválidas");
    const username = screen.getByLabelText(/usuario/i) as HTMLInputElement;
    expect(username.value).toBe("marcela");
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeEnabled();
  });

  it("does not reveal whether a username exists (no existence leak)", () => {
    render(<LoginError />);
    const alert = screen.getByRole("alert");
    // A generic auth error — never "usuario no encontrado"/"no existe" (DS-UI-LOGIN).
    expect(alert.textContent).not.toMatch(/no encontrad/);
    expect(alert.textContent).not.toMatch(/no existe/i);
    expect(alert.textContent).not.toMatch(/usuario existe/i);
  });
});
