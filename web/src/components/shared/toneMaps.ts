import type { BadgeTone } from "../primitives/Badge";

const CASE_STATUS_TONES: Record<string, BadgeTone> = { abierto: "neutral", en_evaluacion: "warning", escalado: "danger", cerrado: "success" };
const CUSTOMER_STATE_TONES: Record<string, BadgeTone> = { nuevo: "warning", activo: "success", inactivo: "neutral", bloqueado: "danger" };
const CONVERSATION_LABELS: Record<string, string> = { bot: "Agente atendiendo", human: "Atención humana", closed: "Cerrada", pending: "En espera", escalated: "Escalado" };
const CUSTOMER_STATE_LABELS: Record<string, string> = { nuevo: "Nuevo", activo: "Activo", inactivo: "Inactivo", bloqueado: "Bloqueado" };
const CASE_STATUS_LABELS: Record<string, string> = { abierto: "Abierto", en_evaluacion: "En evaluación", escalado: "Escalado", cerrado: "Cerrado" };
const KB_STATUS_LABELS: Record<string, string> = { activo: "Activo", deshabilitado: "Deshabilitado", procesando: "Procesando", error: "Error" };
const DIRECTION_LABELS: Record<string, string> = { inbound: "Entrante", outbound: "Saliente" };
const APPOINTMENT_STATUS_TONES: Record<string, BadgeTone> = { booked: "success", cancelled: "neutral", completed: "success", no_show: "danger" };
const APPOINTMENT_STATUS_LABELS: Record<string, string> = { booked: "Reservada", cancelled: "Cancelada", completed: "Completada", no_show: "No asistió" };
const APPOINTMENT_SYNC_TONES: Record<string, BadgeTone> = { pending: "warning", synced: "success", failed: "danger" };
const APPOINTMENT_SYNC_LABELS: Record<string, string> = { pending: "Calendario pendiente", synced: "Calendario sincronizado", failed: "Calendario con error" };

export function caseStatusTone(status: string): BadgeTone { return CASE_STATUS_TONES[status] ?? "neutral"; }
export function customerStateTone(state: string): BadgeTone { return CUSTOMER_STATE_TONES[state] ?? "neutral"; }
export function conversationLabel(state: string): string { return CONVERSATION_LABELS[state] ?? state; }
export function customerStateLabel(state: string): string { return CUSTOMER_STATE_LABELS[state] ?? state; }
export function caseStatusLabel(status: string): string { return CASE_STATUS_LABELS[status] ?? status; }
export function kbStatusLabel(state: string): string { return KB_STATUS_LABELS[state] ?? state; }
export function directionLabel(direction: string): string { return DIRECTION_LABELS[direction] ?? direction; }
export function appointmentStatusTone(status: string): BadgeTone { return APPOINTMENT_STATUS_TONES[status] ?? "neutral"; }
export function appointmentStatusLabel(status: string): string { return APPOINTMENT_STATUS_LABELS[status] ?? status; }
export function appointmentSyncTone(status: string): BadgeTone { return APPOINTMENT_SYNC_TONES[status] ?? "neutral"; }
export function appointmentSyncLabel(status: string): string { return APPOINTMENT_SYNC_LABELS[status] ?? status; }
