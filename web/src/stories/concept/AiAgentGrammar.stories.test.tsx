import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AiAgentGrammarView } from "./AiAgentGrammar.stories";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const defaultProps = { railExpanded: true, inspectorVisible: true, scenario: "emergencia" as const, composerState: "enabled" as const };
const storyRaw = readFileSync(join(process.cwd(), "src", "stories", "concept", "AiAgentGrammar.stories.tsx"), "utf8");
const primitivesRaw = readFileSync(join(process.cwd(), "src", "components", "primitives", "primitives.css"), "utf8");

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

  it("uses the shared tokenized stylesheet without injected styles or hard-coded grammar colors", () => {
    render(<AiAgentGrammarView {...defaultProps} />);
    expect(document.querySelector(".ai-agent-grammar__rail")).toBeInTheDocument();
    expect(document.querySelector("style")).toBeNull();
    expect(storyRaw).not.toMatch(/<style>|const styles/);
    expect(primitivesRaw).toMatch(/\.ai-agent-grammar__rail\s*\{[^}]*background:\s*var\(--primary-800\)/s);
    expect(primitivesRaw).not.toMatch(/\.ai-agent-grammar__rail\s*\{[^}]*#[0-9a-f]{3,8}/i);
  });

  it("exposes accessible regions and honors reduced-motion rules", () => {
    render(<AiAgentGrammarView {...defaultProps} railExpanded={false} inspectorVisible={false} />);
    expect(screen.getByRole("navigation", { name: "Secciones del panel" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Conversación con María González" })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Inspector operacional" })).toBeNull();
    expect(primitivesRaw).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*\.ai-agent-grammar__/);
  });
});
