import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginAuth } from "./LoginAuth";

const source = readFileSync(join(process.cwd(), "src/components/pages/LoginAuth.tsx"), "utf8");

describe("LoginAuth (DS-UI-LOGIN)", () => {
  it("renders the tokenized PageFrame with a desktop brand region and auth form", () => {
    const { container } = render(<LoginAuth />);

    expect(container.querySelector("main.page-frame")).toBeInTheDocument();
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

  it("does not retain the phantom auth card or inline auth chrome", () => {
    expect(source).toContain("PageFrame");
    expect(source).not.toContain("card--auth");
    expect(source).not.toContain("style=");
    expect(source).not.toContain("LOGIN_BRAND_STYLES");
  });
});
