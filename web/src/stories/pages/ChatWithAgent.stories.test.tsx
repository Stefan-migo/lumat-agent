import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatWithAgentView } from "./ChatWithAgent.stories";
import { agentChatMessages } from "./_shared/mockData/chat";

describe("ChatWithAgent Default (R-PRD-PG-11)", () => {
  it("renders the page header, every chat bubble, per-message avatars and idle status", () => {
    render(<ChatWithAgentView status="idle" />);
    expect(screen.getByRole("heading", { name: /asistente lumat/i })).toBeInTheDocument();

    // Every mock message surfaces as a bubble.
    const bubbles = document.querySelectorAll("[data-bubble]");
    expect(bubbles.length).toBe(agentChatMessages.length);

    // Per-message avatar (initials derived from the role) rendered.
    const avatars = document.querySelectorAll(".avatar");
    expect(avatars.length).toBe(agentChatMessages.length);

    // Idle agent status, approved Spanish (DS-UI-COPY).
    expect(screen.getByText("Agente en espera")).toBeInTheDocument();
  });

  it("renders suggestion chips and an enabled neutral composer", () => {
    render(<ChatWithAgentView status="idle" />);
    const chips = screen.getAllByRole("button", { name: /^(agendar|revisar|como)/i });
    expect(chips.length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: /escribe un mensaje/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();
    // Composer placeholder is neutral, never voseo "Escribí" (DS-UI-COPY).
    expect(screen.getByPlaceholderText("Escribe tu mensaje al asistente...")).toBeInTheDocument();
  });
});

describe("ChatWithAgent AgentThinking (R-PRD-PG-11)", () => {
  it("shows the processing spinner and disables the composer", () => {
    render(<ChatWithAgentView status="processing" />);
    expect(document.querySelector(".spinner")).not.toBeNull();
    expect(screen.getByText("Procesando respuesta")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /escribe un mensaje/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("keeps processing truthful without realtime or streaming copy", () => {
    render(<ChatWithAgentView status="processing" />);
    expect(screen.getByRole("status")).toHaveTextContent("Procesando respuesta");
    expect(screen.queryByText(/tiempo real|escribiendo|streaming/i)).toBeNull();
  });
});

describe("ChatWithAgent copy + accessibility (DS-UI-COPY)", () => {
  it("labels every bubble with a Spanish direction-agnostic message label", () => {
    render(<ChatWithAgentView status="idle" />);
    const bubbles = document.querySelectorAll("[data-bubble]");
    bubbles.forEach((b) => {
      const label = b.getAttribute("aria-label") ?? "";
      // No English "admin message"/"agent message" labels (DS-UI-COPY).
      expect(label).not.toMatch(/ message$/);
      expect(/Mensaje de (?:administrador|agente)$/.test(label)).toBe(true);
    });
  });

  it("renders per-role avatars with approved Spanish role initials", () => {
    render(<ChatWithAgentView status="idle" />);
    const avatars = document.querySelectorAll(".avatar");
    // The agent avatar initial must reflect the approved "Agente Lumat" role;
    // every avatar renders non-empty initials (no English role labels leak).
    avatars.forEach((a) => {
      expect((a.textContent ?? "").length).toBeGreaterThan(0);
    });
    expect(Array.from(avatars).some((a) => (a.textContent ?? "").includes("A"))).toBe(true);
  });
});
