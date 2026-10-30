import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AssistantWorkspace } from "./components/pages/AssistantWorkspace";

describe("dbg", () => {
  it("dumps context html", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url === "/panel/api/projects") return new Response(JSON.stringify({ projects: [{ id: 1, slug: "ops", name: "Operaciones", purpose: "Trabajo", status: "active" }] }), { status: 200 });
      return new Response(JSON.stringify({ threads: [] }), { status: 200 });
    });
    render(<AssistantWorkspace onCreateThread={vi.fn()}><p>Thread</p></AssistantWorkspace>);
    const aside = await screen.findByRole("complementary", { name: "Contexto del hilo" });
    console.log("HTMLSTART " + aside.innerHTML.replace(/<svg[\s\S]*?<\/svg>/g, "<svg/>").slice(0, 2500) + " HTMLEND");
    expect(true).toBe(true);
  });
});
