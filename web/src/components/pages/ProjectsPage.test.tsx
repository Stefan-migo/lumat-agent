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

  it("groups SDB artifacts by entity in read-only tables", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null }, artifacts: { "Thread 4": [{ id: 10, entity_id: "Thread 4", topic_key: "requirements/one", tipo: "decision", titulo: "Scope", contenido: "Keep it small", status: "active", created_at: null, updated_at: null }], Design: [{ id: 11, entity_id: "Design", topic_key: "design/one", tipo: "discovery", titulo: "Layout", contenido: "Use tables", status: "needs_review", created_at: null, updated_at: null }] } }), { status: 200 }));
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    expect(await screen.findByRole("region", { name: "Thread 4" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Design" })).toBeInTheDocument();
    expect(screen.getByText("Scope")).toBeInTheDocument();
    expect(screen.getByText("Layout")).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader", { name: "Título" })).toHaveLength(2);
    expect(screen.queryByText("requirements/one")).not.toBeInTheDocument();
    expect(screen.queryByText("design/one")).not.toBeInTheDocument();
  });

  it("renders the project status and back control in the detail header", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null }, artifacts: {} }), { status: 200 }));
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} />);
    expect(await screen.findByText("Run ops · Activo")).toBeInTheDocument();
    expect(screen.getByText("Run ops · Activo").closest("p")).toBeInTheDocument();
    expect(screen.getByText("Run ops · Activo").closest("p")?.querySelector(".badge")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Volver a proyectos" }));
    expect(back).toHaveBeenCalled();
  });

  it("offers a project-bound assistant entry point", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ project: { id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null }, artifacts: {} }), { status: 200 }));
    const onOpenChat = vi.fn();
    render(<ProjectsPage projectSlug="ops" data={{ projects: [] }} onOpenChat={onOpenChat} />);

    fireEvent.click(await screen.findByRole("button", { name: /abrir asistente/i }));

    expect(onOpenChat).toHaveBeenCalledWith("ops");
  });
});
