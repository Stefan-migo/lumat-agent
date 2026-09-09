import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginAuth } from "./LoginAuth";

const source = readFileSync(join(process.cwd(), "src/components/pages/LoginAuth.tsx"), "utf8");
const primitives = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");

describe("LoginAuth (DS-UI-LOGIN)", () => {
  it("renders the centered full-viewport login page with brand lockup and auth form", () => {
    const { container } = render(<LoginAuth />);

    expect(container.querySelector("main.login-page")).toBeInTheDocument();
    expect(screen.getByText("Lumat")).toBeInTheDocument();
    expect(screen.getByText("Panel operativo")).toBeInTheDocument();
    expect(screen.getByRole("form")).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("keeps the username and generic Spanish error safe after a failed login", () => {
    render(<LoginAuth error="Credenciales inválidas" username="marcela" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Credenciales inválidas");
    expect(screen.getByLabelText("Usuario")).toHaveValue("marcela");
    expect(screen.getByRole("alert")).not.toHaveTextContent(/no existe|no encontrado/i);
  });

  it("has no top welcome heading or phantom auth chrome", () => {
    expect(source).not.toContain("Bienvenido");
    expect(source).not.toContain("card--auth");
    expect(source).not.toContain("style=");
    expect(source).not.toContain("LOGIN_BRAND_STYLES");
    expect(source).toContain("login-page");
  });

  it("defines a centered full-viewport page and desktop split/mobile stacked frame with design tokens", () => {
    expect(primitives).toMatch(/\.login-page[\s\S]*?min-height:\s*100dvh/);
    expect(primitives).toMatch(/\.login-page[\s\S]*?var\(--/);
    expect(primitives).toMatch(/\.login-frame[\s\S]*?grid-template-columns:/);
    expect(primitives).toMatch(/\.login-frame[\s\S]*?var\(--/);
    expect(primitives).toMatch(/@media \(max-width: 40rem\)[\s\S]*?\.login-frame[\s\S]*?grid-template-columns:\s*1fr/);
  });
});
