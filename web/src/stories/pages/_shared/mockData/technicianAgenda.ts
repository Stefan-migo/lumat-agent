import type { TechnicianAppointment } from "../../../../types";

// A fixed clock: day labels ("Hoy", "Mañana", a dated day) must not change with
// the run date, or every story screenshot would drift.
export const agendaNow = new Date("2026-09-19T12:00:00-03:00");

/** A past day, today, tomorrow and a later day — the shape TECH-AGENDA-1 returns. */
export const agendaData: TechnicianAppointment[] = [
  {
    id: 5, service: "Reparación de cañería en cocina", local_start: "2026-09-15T11:00:00",
    starts_at: "2026-09-15T14:00:00+00:00", ends_at: "2026-09-15T15:00:00+00:00", timezone: "America/Santiago",
    customer: { name: "Cliente Demo H3", address: "Av. Siempre Viva 123", comuna: "Providencia", phone: "+56910001000" },
    case_summary: "Revisar fuga del calefont",
  },
  {
    id: 6, service: "Revisión de calefont", local_start: "2026-09-19T15:00:00",
    starts_at: "2026-09-19T18:00:00+00:00", ends_at: "2026-09-19T19:00:00+00:00", timezone: "America/Santiago",
    customer: { name: "María Silva", address: "Los Alerces 42", comuna: "Ñuñoa", phone: "+56912345678" },
    case_summary: "El cliente reporta que la instalación provisoria de agua caliente no tiene presión suficiente en el segundo piso y solicita una evaluación técnica completa antes de la entrega de la obra.",
  },
  {
    id: 7, service: "Cambio de termo", local_start: "2026-09-20T09:00:00",
    starts_at: "2026-09-20T12:00:00+00:00", ends_at: "2026-09-20T13:00:00+00:00", timezone: "America/Santiago",
    customer: { name: null, address: null, comuna: null, phone: null },
    case_summary: null,
  },
  {
    id: 8, service: "Instalación de llave", local_start: "2026-09-26T09:00:00",
    starts_at: "2026-09-26T12:00:00+00:00", ends_at: "2026-09-26T13:00:00+00:00", timezone: "America/Santiago",
    customer: { name: "Constructora Los Andes SpA", address: "Camino Rural Km 14, sector El Maitén, parcela 7", comuna: "San Bernardo", phone: "+56987654321" },
    case_summary: null,
  },
];

/** The same roster with no customer data at all, to review every fallback string. */
export const agendaWithoutCustomer: TechnicianAppointment[] = agendaData.map((row) => ({
  ...row,
  customer: { name: null, address: null, comuna: null, phone: null },
  case_summary: null,
}));

/** A long roster, to review how the day groups hold up past one screen. */
export const agendaLong: TechnicianAppointment[] = Array.from({ length: 12 }, (_, index) => ({
  id: 100 + index,
  service: `Mantención programada número ${index + 1}`,
  local_start: "2026-09-19T09:00:00",
  starts_at: new Date(Date.UTC(2026, 8, 19 + index, 12, 0)).toISOString(),
  ends_at: new Date(Date.UTC(2026, 8, 19 + index, 13, 0)).toISOString(),
  timezone: "America/Santiago",
  customer: { name: `Cliente ${index + 1}`, address: `Calle Falsa ${100 + index}`, comuna: "Ñuñoa", phone: "+56900000000" },
  case_summary: index % 3 === 0 ? "Sin acceso al domicilio en el intento anterior." : null,
}));
