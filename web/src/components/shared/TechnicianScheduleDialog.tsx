import { useEffect, useState } from "react";
import { ApiError, getTechnicianSchedule, saveTechnicianSchedule } from "../../api";
import type { TechnicianScheduleEntry, UserRef } from "../../types";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";
import { StateMessage } from "./StateMessage";
import "./TechnicianScheduleDialog.css";

const SHORT_DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const INVALID_SCHEDULE_MESSAGE = "El horario de fin debe ser posterior al de inicio.";
type DaySchedule = { enabled: boolean; opens_at: string; closes_at: string };
type DialogState = "loading" | "ready" | "saving" | "saved" | "load-error" | "server-error";

const emptyWeek = (): DaySchedule[] => SHORT_DAYS.map(() => ({ enabled: false, opens_at: "09:00", closes_at: "18:00" }));

export function TechnicianScheduleDialog({ open, technician, onClose, onSaved }: {
  open: boolean;
  technician: UserRef;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const [state, setState] = useState<DialogState>("loading");
  const [week, setWeek] = useState<DaySchedule[]>(emptyWeek);
  const [error, setError] = useState("");
  const invalid = week.some(({ enabled, opens_at, closes_at }) => enabled && (!opens_at || !closes_at || opens_at >= closes_at));

  const loadSchedule = () => {
    setState("loading");
    setError("");
    void getTechnicianSchedule(technician.id).then(({ schedule }) => {
      const next = emptyWeek();
      schedule.forEach(({ weekday, opens_at, closes_at }) => {
        if (weekday >= 1 && weekday <= 7) next[weekday - 1] = { enabled: true, opens_at: opens_at.slice(0, 5), closes_at: closes_at.slice(0, 5) };
      });
      setWeek(next);
      setState("ready");
    }).catch(() => setState("load-error"));
  };

  useEffect(() => {
    if (open) loadSchedule();
  }, [open, technician.id]);

  const updateDay = (index: number, update: Partial<DaySchedule>) => {
    setWeek((days) => days.map((day, dayIndex) => dayIndex === index ? { ...day, ...update } : day));
    setState("ready");
    setError("");
  };

  const save = async () => {
    if (invalid || state === "saving") return;
    setState("saving");
    setError("");
    try {
      const schedule: TechnicianScheduleEntry[] = week.flatMap(({ enabled, opens_at, closes_at }, index) => enabled ? [{ weekday: index + 1, opens_at, closes_at }] : []);
      await saveTechnicianSchedule(technician.id, schedule);
      setState("saved");
      onSaved?.();
    } catch (cause) {
      setState("server-error");
      setError(cause instanceof ApiError && cause.structuredDetail?.code === "invalid_schedule"
        ? "Revisa los horarios ingresados."
        : "No pudimos guardar el horario. Intenta nuevamente.");
    }
  };

  const saving = state === "saving";
  return <Dialog open={open} onClose={() => { if (!saving) onClose(); }} title="Horario semanal" description={`Define los días y horarios de atención de ${technician.username}.`}>
    {state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando horario" /> : null}
    {state === "load-error" ? <div className="technician-schedule__feedback"><StateMessage tone="danger" role="alert" title="No pudimos cargar el horario" detail="Intenta nuevamente para recuperar la disponibilidad." /><Button variant="secondary" onClick={loadSchedule}>Reintentar</Button></div> : null}
    {state !== "loading" && state !== "load-error" ? <>
      <div className="technician-schedule" aria-label="Días y horarios de atención">
        {week.map((day, index) => <div className="technician-schedule__row" key={index}>
          <Button variant="secondary" className="technician-schedule__day" aria-pressed={day.enabled} disabled={saving} onClick={() => updateDay(index, { enabled: !day.enabled })}>{SHORT_DAYS[index]}</Button>
          <Input label={`Inicio ${SHORT_DAYS[index]}`} type="time" value={day.opens_at} disabled={!day.enabled || saving} aria-describedby={invalid && day.enabled ? "technician-schedule-validation" : undefined} onChange={(event) => updateDay(index, { opens_at: event.target.value })} />
          <Input label={`Fin ${SHORT_DAYS[index]}`} type="time" value={day.closes_at} disabled={!day.enabled || saving} aria-describedby={invalid && day.enabled ? "technician-schedule-validation" : undefined} onChange={(event) => updateDay(index, { closes_at: event.target.value })} />
        </div>)}
      </div>
      {invalid ? <p id="technician-schedule-validation" className="technician-schedule__error" role="alert">{INVALID_SCHEDULE_MESSAGE}</p> : null}
      {state === "server-error" ? <StateMessage tone="danger" role="alert" title={error} /> : null}
      {state === "saved" ? <StateMessage tone="success" role="status" title="Horario guardado" /> : null}
      <div className="technician-schedule__footer">
        <Button variant="secondary" disabled={saving} onClick={onClose}>Cancelar</Button>
        <Button disabled={saving || invalid} onClick={() => void save()}>{saving ? "Guardando…" : "Guardar horario"}</Button>
      </div>
    </> : null}
  </Dialog>;
}
