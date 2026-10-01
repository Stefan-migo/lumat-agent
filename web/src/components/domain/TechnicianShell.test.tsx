import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TechnicianShell } from "./TechnicianShell";
import type { User } from "../../types";

vi.mock("../pages/AgentChat", () => ({ AgentChat: ({ sectionTabs, onThreadOpened, role }: { sectionTabs: React.ReactNode; onThreadOpened: (id: number) => void; role: string }) => <section><h1>AgentChat role={role}</h1>{sectionTabs}<button onClick={() => onThreadOpened(11)}>Open thread</button></section> }));
vi.mock("../pages/ProjectsPage", () => ({ ProjectsPage: ({ sectionTabs }: { sectionTabs: React.ReactNode }) => <section><h1>ProjectsPage</h1>{sectionTabs}</section> }));
vi.mock("../pages/PlanningSessions", () => ({ PlanningSessions: ({ sectionTabs }: { sectionTabs: React.ReactNode }) => <section><h1>PlanningSessions</h1>{sectionTabs}</section> }));
vi.mock("../pages/TechnicianAgenda", () => ({ TechnicianAgenda: () => <h1>TechnicianAgenda</h1> }));
vi.mock("../pages/SelfProfile", () => ({ SelfProfile: () => <h1>Mi perfil</h1> }));

const tecnico: User = { username: "teo", role: "tecnico" };

beforeEach(() => window.history.replaceState({}, "", "/panel/app/agenda"));
afterEach(() => window.history.replaceState({}, "", "/panel/app/agenda"));

describe("TechnicianShell routing", () => {
  it.each(["/panel/app/agenda", "/panel/app/clients", "/panel/app/conversations", "/panel/app/dashboard"]) (
    "keeps %s on the agenda unless it is an allowed technician route",
    (path) => {
      window.history.replaceState({}, "", path);
      render(<TechnicianShell user={tecnico} />);
      expect(screen.getByRole("heading", { name: "TechnicianAgenda" })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/panel/app/agenda");
    },
  );

  it("navigates across assistant sections with URL-backed tabs and marks the active route", async () => {
    render(<TechnicianShell user={tecnico} />);
    fireEvent.click(screen.getByRole("button", { name: "Asistente" }));
    expect(await screen.findByRole("heading", { name: "AgentChat role=tecnico" })).toBeInTheDocument();
    const tabs = screen.getByRole("tablist", { name: "Secciones del asistente" });
    for (const label of ["Chat", "Proyectos", "Sesiones de planificación"]) expect(within(tabs).getByRole("tab", { name: label })).toBeInTheDocument();
    expect(within(tabs).getByRole("tab", { name: "Chat" })).toHaveAttribute("aria-selected", "true");
    await userEvent.setup().click(within(tabs).getByRole("tab", { name: "Proyectos" }));
    expect(window.location.pathname).toBe("/panel/app/projects");
    expect(await screen.findByRole("heading", { name: "ProjectsPage" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/panel/app/projects");
    expect(screen.getByRole("tab", { name: "Proyectos" })).toHaveAttribute("aria-selected", "true");
  });

  it("resolves allowed deep links and denies disallowed views on browser navigation", async () => {
    window.history.replaceState({}, "", "/panel/app/planning-sessions/session-a");
    render(<TechnicianShell user={tecnico} />);
    expect(screen.getByRole("heading", { name: "PlanningSessions" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/panel/app/planning-sessions/session-a");
    window.history.pushState({}, "", "/panel/app/users");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => expect(screen.getByRole("heading", { name: "TechnicianAgenda" })).toBeInTheDocument());
    expect(window.location.pathname).toBe("/panel/app/agenda");
  });

  it("opens chat from the agenda nav and marks the active nav item", async () => {
    render(<TechnicianShell user={tecnico} />);
    const nav = screen.getByRole("navigation", { name: "Navegación del técnico" });
    expect(within(nav).getByRole("button", { name: "Agenda" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(within(nav).getByRole("button", { name: "Asistente" }));
    expect(await screen.findByRole("heading", { name: "AgentChat role=tecnico" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Asistente" })).toHaveAttribute("aria-current", "page");
  });

  it("lets a technician open their profile from the shell entry", async () => {
    window.history.replaceState({}, "", "/panel/app/agenda");
    render(<TechnicianShell user={tecnico} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Mi perfil" }));
    expect(await screen.findByRole("heading", { name: "Mi perfil" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/panel/app/profile");
  });
});
