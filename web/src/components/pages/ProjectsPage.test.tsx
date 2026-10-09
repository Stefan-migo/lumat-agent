import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ProjectsPage } from "./ProjectsPage";
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
    render(<ProjectsPage />);
    await fillProjectForm();
    expect(await screen.findByRole("button", { name: "Operations" })).toBeInTheDocument();
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
    render(<ProjectsPage />);
    await fillProjectForm();
    expect(await screen.findByRole("alert")).toHaveTextContent("Slug already exists");
  });

  it("shows candidates for ambiguous project purposes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ projects: [] }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Purpose is ambiguous", candidates: [{ slug: "ops", name: "Operations", similarity: 0.82 }] }), { status: 409 }));
    render(<ProjectsPage />);
    await fillProjectForm();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Purpose is ambiguous");
    expect(alert).toHaveTextContent("Operations (ops)");
    expect(alert).toHaveTextContent("0.82");
  });

  it("renders the project status and back control in the detail header", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 })).mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    expect(await screen.findByText("Run ops · Activo")).toBeInTheDocument();
    expect(screen.getByText("Run ops · Activo").closest("p")).toBeInTheDocument();
    expect(screen.getByText("Run ops · Activo").closest("p")?.querySelector(".badge")).toBeNull();
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

    expect(await screen.findByText("Run ops · Activo")).toBeInTheDocument();
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
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null, config: { instructions: "Existing instructions", tool_policy: { opt_in_enabled: [] }, skills: [] } } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null, config: { instructions: "Answer in Spanish.", tool_policy: { opt_in_enabled: [] }, skills: [] } } }), { status: 200 }))
      .mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);

    const textarea = await screen.findByLabelText("Instrucciones del proyecto");
    expect(textarea).toHaveValue("Existing instructions");
    fireEvent.change(textarea, { target: { value: "Answer in Spanish." } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByLabelText("Instrucciones del proyecto")).toHaveValue("Answer in Spanish.");
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ instructions: "Answer in Spanish." }) }));
  });

  it("explains that project-scoped threads are not supported and shows an honest agent empty state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null } }), { status: 200 })).mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    await screen.findByRole("tab", { name: "Hilos" });

    fireEvent.mouseDown(screen.getByRole("tab", { name: "Hilos" }), { button: 0 });
    expect(await screen.findByText("Esta vista todavía no puede filtrar hilos por proyecto. La API no entrega la asociación del proyecto en el listado de hilos.")).toBeInTheDocument();
    expect(screen.queryByText(/Conversación|thread/i)).not.toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("tab", { name: "Agentes" }), { button: 0 });
    expect(await screen.findByText("La gestión de agentes por proyecto todavía no está disponible.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Skills" })).toBeInTheDocument();
  });

  it("shows a not-found state for an unknown project", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Project not found" }), { status: 404 }));
    render(<ProjectsPage projectSlug="missing" data={{ projects: [] }} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No encontramos este proyecto");
  });
});
