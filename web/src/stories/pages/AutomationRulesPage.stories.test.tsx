import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  AutomationRulesPageStory,
  Data,
  Empty,
  Error,
  Forbidden,
  Loading,
  OperatorData,
} from "./AutomationRulesPage.stories";

describe("AutomationRulesPage Storybook state matrix", () => {
  it("renders the production-shaped data story", () => {
    render(<AutomationRulesPageStory {...(Data.args ?? {})} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Avisar caso nuevo" })).toBeInTheDocument();
    expect(screen.getByText("Contenido de notificación")).toBeInTheDocument();
    expect(screen.getByText("Habilitada")).toBeInTheDocument();
  });

  it.each([
    [Loading, "Cargando reglas"],
    [Empty, "No hay reglas de automatización"],
    [Error, "No pudimos cargar las reglas"],
    [Forbidden, "No tienes permiso para ver las reglas"],
  ])("renders the %s state", (story, label) => {
    render(<AutomationRulesPageStory {...(story.args ?? {})} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("renders the operator story without mutation controls", () => {
    render(<AutomationRulesPageStory {...(OperatorData.args ?? {})} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear regla" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar|habilitar|deshabilitar/i })).not.toBeInTheDocument();
  });
});
