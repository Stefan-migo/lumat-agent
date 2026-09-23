import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "../domain/AppShell";
import { parsePanelPath, pathForRoute } from "../domain/panelRoutes";
import { docs } from "../../stories/pages/_shared/mockData/kb";
import type { KbDocument, User } from "../../types";

const admin: User = { username: "ana", role: "admin" };
const document = { ...docs[0], content: "Contenido del documento." } satisfies KbDocument;

beforeEach(() => {
  window.history.replaceState({}, "", "/panel/app/kb/1");
});

afterEach(() => {
  window.history.replaceState({}, "", "/panel/app/");
  vi.restoreAllMocks();
});

describe("KB document detail route", () => {
  it("builds and parses a KB document route", () => {
    expect(pathForRoute({ view: "kb", kbDocId: document.id })).toBe(`/panel/app/kb/${document.id}`);
    expect(parsePanelPath(`/panel/app/kb/${document.id}`)).toEqual({ view: "kb", kbDocId: document.id });
  });

  it("renders the detail for a document route with the shared back control", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input), "http://localhost").pathname;
      if (path === "/panel/api/notifications") return new Response(JSON.stringify({ notifications: [] }), { status: 200 });
      if (path === `/panel/api/kb/${document.id}`) return new Response(JSON.stringify(document), { status: 200 });
      return new Response(JSON.stringify({ docs: [] }), { status: 200 });
    });

    render(<AppShell user={admin} />);

    expect(await screen.findByRole("heading", { name: document.title })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver a documentos" })).toBeInTheDocument();
  });
});
