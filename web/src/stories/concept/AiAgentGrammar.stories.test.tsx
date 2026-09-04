import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AiAgentGrammarView } from "./AiAgentGrammar.stories";

const defaultProps = { railExpanded: true, inspectorVisible: true, scenario: "emergencia" as const, composerState: "enabled" as const };

describe("AI-agent grammar concept page", () => {
  it("renders the operational shell, agent events, and inspector roles", () => {
    render(<AiAgentGrammarView {...defaultProps} />);
    expect(screen.getByRole("heading", { name: "Conversación · María González" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Navegación principal" })).toBeInTheDocument();
    expect(screen.getByText("Lumat clasificó la solicitud")).toBeInTheDocument();
    expect(screen.getByText("Detectó emergencia probable")).toBeInTheDocument();
    expect(screen.getByText("Derivó a atención humana")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reconocer emergencia" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Respuesta" })).toBeEnabled();
  });

  it("makes disabled composer reasons explicit and supports the routine visit scenario", () => {
    render(<AiAgentGrammarView {...defaultProps} scenario="visita" composerState="disabled_not_taken" />);
    expect(screen.getByText("Lumat consultó la base de conocimientos · Creó una solicitud de visita")).toBeInTheDocument();
    expect(screen.queryByText("Detectó emergencia probable")).toBeNull();
    expect(screen.getAllByText("Toma la conversación para responder").length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: "Respuesta" })).toBeDisabled();
    expect(screen.getByText("Revisión de calefacción")).toBeInTheDocument();
    expect(screen.getByText("Solicitud de visita creada")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reconocer emergencia" })).toBeNull();
  });
});
