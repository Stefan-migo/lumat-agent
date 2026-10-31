import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProjectsPage } from "./ProjectsPage";
import { ToastProvider } from "../primitives/Toast";
import { parsePanelPath, pathForView } from "../domain/panelRoutes";

describe("projects panel", () => {
  afterEach(() => vi.restoreAllMocks());
  it("parses and emits the project route", () => {
    expect(parsePanelPath("/panel/app/projects")).toEqual({ view: "projects" });
    expect(pathForView("projects")).toBe("/panel/app/projects");
  });

  it("renders project records as a read-only table and opens the detail route", () => {
    const onOpenProject = vi.fn();
    render(<ProjectsPage data={{ projects: [{ id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "archived", created_at: null, updated_at: null }] }} state="ready" onOpenProject={onOpenProject} />);
    expect(screen.getByRole("columnheader", { name: "Proyecto" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Operations" }));
    expect(onOpenProject).toHaveBeenCalledWith("ops");
    expect(screen.queryByRole("button", { name: /renombrar|archivar|fusionar/i })).not.toBeInTheDocument();
  });

  const fillProjectForm = async () => {
    fireEvent.change(await screen.findByLabelText("Slug"), { target: { value: "ops" } });
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Operations" } });
    fireEvent.change(screen.getByLabelText("Propósito"), { target: { value: "Run operations" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear proyecto" }));
  };

  it("creates a project and refreshes the project list", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ projects: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 2, slug: "ops", name: "Operations", purpose: "Run operations", status: "active" } }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ projects: [{ id: 2, slug: "ops", name: "Operations", purpose: "Run operations", status: "active" }] }), { status: 200 }));
    render(<ToastProvider><ProjectsPage /></ToastProvider>);
    await fillProjectForm();
    expect(await screen.findByRole("button", { name: "Operations" })).toBeInTheDocument();
    expect(await screen.findByText("Proyecto creado.", { selector: ".toast__message" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/panel/api/projects", expect.objectContaining({ method: "POST", body: JSON.stringify({ slug: "ops", name: "Operations", purpose: "Run operations" }) }));
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("keeps the created project visible when the refresh fails", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ projects: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 2, slug: "ops", name: "Operations", purpose: "Run operations", status: "active" } }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "boom" }), { status: 500 }));
    render(<ProjectsPage />);
    await fillProjectForm();
    expect(await screen.findByRole("button", { name: "Operations" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Slug")).toHaveValue("");
  });

  it("shows duplicate slug conflicts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ projects: [] }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Slug already exists" }), { status: 409 }));
    render(<ToastProvider><ProjectsPage /></ToastProvider>);
    await fillProjectForm();
    expect(await screen.findByText("Slug already exists", { selector: ".toast__message" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows candidates for ambiguous project purposes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ projects: [] }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Purpose is ambiguous", candidates: [{ slug: "ops", name: "Operations", similarity: 0.82 }] }), { status: 409 }));
    render(<ToastProvider><ProjectsPage /></ToastProvider>);
    await fillProjectForm();
    const toast = await screen.findByText(/Purpose is ambiguous/, { selector: ".toast__message" });
    expect(toast).toHaveTextContent("Operations (ops)");
    expect(toast).toHaveTextContent("0.82");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the project status and back control in the detail header", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 })).mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    const header = (await screen.findByRole("heading", { level: 1, name: "Operations" })).closest(".page-header");
    expect(header).toHaveTextContent("Run ops");
    expect(header?.querySelector(".badge")).toHaveTextContent("Activo");
    fireEvent.click(screen.getByRole("button", { name: "Volver a proyectos" }));
    expect(back).toHaveBeenCalled();
  });

  it("offers a project-bound assistant entry point", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 })).mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    const onOpenChat = vi.fn();
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} onOpenChat={onOpenChat} />);

    fireEvent.click(await screen.findByRole("button", { name: /abrir asistente/i }));

    expect(onOpenChat).toHaveBeenCalledWith("ops");
  });

  it("renders editable instructions while keeping project identity and resource controls disabled", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 })).mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);

    const header = (await screen.findByRole("heading", { level: 1, name: "Operations" })).closest(".page-header");
    expect(header).toHaveTextContent("Run ops");
    expect(screen.getByRole("tab", { name: "Contexto" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Nombre del proyecto")).toHaveValue("Operations");
    expect(screen.getByLabelText("Nombre del proyecto")).toBeDisabled();
    expect(screen.getByLabelText("Propósito")).toHaveValue("Run ops");
    expect(screen.getByLabelText("Instrucciones del proyecto")).toHaveValue("");
    expect(screen.getByLabelText("Instrucciones del proyecto")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    expect(await screen.findByRole("heading", { name: "Archivos del proyecto" })).toBeInTheDocument();
  });

  it("saves project instructions through the config endpoint", async () => {
    const project = (instructions: string) => ({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null, config: { instructions, tool_policy: { opt_in_enabled: [] }, skills: [] } } });
    // Keyed by URL, not by call order: ProjectResources also fetches on mount, so a sequence of
    // mockResolvedValueOnce handed the PATCH someone else's response and the save silently failed
    // while the old assertion (local textarea state) still passed.
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/projects/ops/config" && init?.method === "PATCH") return new Response(JSON.stringify(project("Answer in Spanish.")), { status: 200 });
      if (url === "/panel/api/projects/ops") return new Response(JSON.stringify(project("Existing instructions")), { status: 200 });
      return new Response(JSON.stringify({ files: [] }), { status: 200 });
    });
    render(<ToastProvider><ProjectsPage projectSlug="ops" data={{ projects: [] }} /></ToastProvider>);

    const textarea = await screen.findByLabelText("Instrucciones del proyecto");
    expect(textarea).toHaveValue("Existing instructions");
    fireEvent.change(textarea, { target: { value: "Answer in Spanish." } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ instructions: "Answer in Spanish." }) })));
    expect(await screen.findByLabelText("Instrucciones del proyecto")).toHaveValue("Answer in Spanish.");
    expect(await screen.findByText("Instrucciones guardadas.", { selector: ".toast__message" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ instructions: "Answer in Spanish." }) }));
  });

  it("wires the Hilos tab to the project thread list and loads the project agent roster", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/chat/threads")) return new Response(JSON.stringify({ threads: [{ id: 5, title: "Revisión de herramientas", proyecto: "ops", created_at: null, updated_at: null, run_status: null, approval_status: null, preview: "Consulta de las herramientas disponibles." }] }), { status: 200 });
      if (url.includes("/panel/api/projects/ops/agents")) return new Response(JSON.stringify({ agents: [], latest_run: null }), { status: 200 });
      if (url.includes("/panel/api/projects/ops/files")) return new Response(JSON.stringify({ files: [] }), { status: 200 });
      if (url.includes("/panel/api/projects/ops/folders")) return new Response(JSON.stringify({ folders: [] }), { status: 200 });
      if (url.includes("/panel/api/projects/ops")) return new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    await screen.findByRole("tab", { name: "Hilos" });

    fireEvent.mouseDown(screen.getByRole("tab", { name: "Hilos" }), { button: 0 });
    expect(await screen.findByText("Revisión de herramientas")).toBeInTheDocument();
    expect(screen.getByText("Consulta de las herramientas disponibles.")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("tab", { name: "Agentes" }), { button: 0 });
    expect(await screen.findByRole("heading", { name: "Agentes del proyecto" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Skills" })).toBeInTheDocument();
  });

  it("shows a not-found state for an unknown project", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Project not found" }), { status: 404 }));
    render(<ProjectsPage projectSlug="missing" data={{ projects: [] }} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No encontramos este proyecto");
  });
});
