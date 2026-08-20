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

    // Idle agent status text.
    expect(screen.getByText("Agent idle")).toBeInTheDocument();
  });

  it("renders suggestion chips and an enabled composer", () => {
    render(<ChatWithAgentView status="idle" />);
    const chips = screen.getAllByRole("button", { name: /^(agendar|revisar|como)/i });
    expect(chips.length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: /escribe un mensaje/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();
  });
});

describe("ChatWithAgent AgentThinking (R-PRD-PG-11)", () => {
  it("shows the processing spinner and disables the composer", () => {
    render(<ChatWithAgentView status="processing" />);
    expect(document.querySelector(".spinner")).not.toBeNull();
    expect(screen.getByText(/agent is thinking/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /escribe un mensaje/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });
});
