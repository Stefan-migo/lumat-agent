import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings as SettingsData } from "../../types";
import { Settings } from "./Settings";

const settings = (overrides: Partial<SettingsData> = {}): SettingsData => ({
  model_api_key: { configured: false, source: "none", masked: "" },
  email: { host: "localhost", port: 25, from_address: "notificaciones@lumat.cl", user: "", tls: "none", password: { configured: false, masked: "" } },
  scope_rules: { general: "bot_resolve" }, keywords: ["gas"], tone: "cercano",
  messages: { greeting: "Hola", greeting_short: "Hola, ¿qué necesitas?", greeting_name: "Hola, Ana", greeting_short_name: "Hola, Ana", smalltalk: "Con gusto.", cannot_answer: "No sé", clarification: "¿Cuál?", cannot_understand_offer: "¿Visitamos o te atiende una persona?", kb_miss_offer: "No tengo ese dato.", farewell: "Chao", out_of_hours: "Cerrado" },
  templates: [],
  hours: { timezone: "America/Santiago", schedule: [{ days: [1], open: "09:00", close: "18:00" }] },
  tarifa: { visita_tecnica: [{ desde_mes: 1, hasta_mes: 12, valor: 30000 }], mantencion_calefont: [{ desde_mes: 1, hasta_mes: 12, valor: 50000 }], mantencion_caldera: [{ desde_mes: 1, hasta_mes: 12, valor: 80000 }], lavado_red: [{ desde_mes: 1, hasta_mes: 12, valor: 140000 }] },
  coverage: ["Las Condes"], service_durations: {}, booking: { lead_hours: 2 },
  conversation_limit: 4, daily_limit: 20, meta_cost: 0.05,
  persona: { orchestrator: "Eres Max.", orchestrator_brief: "Sé breve.", customized: false },
  emergency: { safety_instructions: ["Corta el gas."], contacts: ["Bomberos 132."], notify_message: "Notificado.", customized: false },
  conduct: {
    orden: ["failure", "comuna", "name"],
    redaccion: "plantilla",
    max_preguntas_por_mensaje: 1,
    derivaciones: ["cobertura"],
    customized: false,
    options: {
      redaccion: ["llm", "plantilla"],
      fields: [
        { value: "failure", label: "Problema" },
        { value: "equipment", label: "Equipo" },
        { value: "comuna", label: "Comuna" },
        { value: "availability", label: "Disponibilidad" },
        { value: "name", label: "Nombre" },
        { value: "email", label: "Correo" },
        { value: "address", label: "Dirección" },
      ],
      max_preguntas_por_mensaje: [1, 2],
      derivaciones: ["cobertura"],
    },
  },
  capture_questions: { questions: { failure: "¿Qué pasa con el equipo?", comuna: "¿En qué comuna estás?", name: "¿Cuál es tu nombre?" }, customized: false },
  reply_texts: { texts: { booking_offer: "Horarios: {{opciones}}", manage_kept: "Quedó igual." }, slots: { booking_offer: ["opciones"], manage_kept: [] }, customized: false },
  snapshot: { date: "2026-10-08", conversation_spend: 1, conversation_limit: 4, conversation_percent: 25, daily_spend: 2, daily_limit: 20, daily_percent: 10, mode: "normal" },
  ...overrides,
});
const capabilities = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };

describe("Settings — Correo section", () => {
  afterEach(() => vi.restoreAllMocks());

  it("saves the SMTP configuration", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, email: { host: "mail.lumat.cl", port: 587, from_address: "sistema@lumat.cl", user: "", tls: "starttls", password: { configured: false, masked: "" } } }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Integraciones" }));
    await user.click(screen.getByRole("tab", { name: "Correo" }));
    fireEvent.change(screen.getByLabelText("Servidor SMTP"), { target: { value: "mail.lumat.cl" } });
    fireEvent.change(screen.getByLabelText("Puerto"), { target: { value: "587" } });
    fireEvent.change(screen.getByLabelText("Remitente"), { target: { value: "sistema@lumat.cl" } });
    fireEvent.change(screen.getByLabelText("Seguridad"), { target: { value: "starttls" } });
    await user.click(screen.getByRole("button", { name: "Guardar correo" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/settings/email", expect.objectContaining({ method: "POST" })));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ host: "mail.lumat.cl", port: 587, from_address: "sistema@lumat.cl", user: "", tls: "starttls" });
    expect(await screen.findByText("Configuración de correo guardada.")).toBeInTheDocument();
  });

  it("stores and clears the SMTP password", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, email: { password: { configured: true, masked: "…2468" } } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, email: { password: { configured: false, masked: "" } } }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Integraciones" }));
    await user.click(screen.getByRole("tab", { name: "Correo" }));
    expect(screen.getByText("Sin contraseña guardada")).toBeInTheDocument();
    const passwordInput = screen.getByLabelText("Contraseña SMTP");
    expect(passwordInput).toHaveAttribute("type", "password");
    await user.type(passwordInput, "smtp-pass-2468");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    expect(await screen.findByText("…2468")).toBeInTheDocument();
    expect(passwordInput).toHaveValue("");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ password: "smtp-pass-2468" });
    await user.click(screen.getByRole("button", { name: "Borrar contraseña" }));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith("/panel/api/settings/email/password", expect.objectContaining({ method: "DELETE" })));
    expect(await screen.findByText("Contraseña eliminada del panel.")).toBeInTheDocument();
  });
});
