import { useEffect, useState } from "react";
import { ApiError, getTechnicianSchedule, saveTechnicianSchedule } from "../../api";
import type { TechnicianScheduleEntry, UserRef } from "../../types";
import { Button } from "../primitives/Button";
import { Input } from "../primitives/Input";
import { StateMessage } from "./StateMessage";
import "./TechnicianScheduleEditor.css";

const DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
type Day = { enabled: boolean; opens_at: string; closes_at: string };
const emptyWeek = (): Day[] => DAYS.map(() => ({ enabled: false, opens_at: "09:00", closes_at: "18:00" }));
export function formatTechnicianSchedule(schedule: TechnicianScheduleEntry[]): string {
  if (!schedule.length) return "Sin horario";
  const days = [...schedule].sort((left, right) => left.weekday - right.weekday);
  const groups: TechnicianScheduleEntry[][] = [];
  days.forEach((entry) => {
    const previous = groups.at(-1);
    const last = previous?.at(-1);
    if (previous && last && last.weekday === entry.weekday - 1 && last.opens_at === entry.opens_at && last.closes_at === entry.closes_at) previous.push(entry);
    else groups.push([entry]);
  });
  return groups.map((group) => {
    const first = group[0];
    const last = group.at(-1)!;
    const day = first.weekday === last.weekday ? DAYS[first.weekday - 1] : `${DAYS[first.weekday - 1]}–${DAYS[last.weekday - 1]}`;
    return `${day} ${first.opens_at.slice(0, 5)}–${first.closes_at.slice(0, 5)}`;
  }).join(" · ");
}

export function TechnicianScheduleEditor({ technician, onSaved }: { technician: UserRef; onSaved: (summary: string) => void }) {
  const [state, setState] = useState<"loading" | "load-error" | "ready" | "saving" | "saved" | "error">("loading");
  const [week, setWeek] = useState<Day[]>(emptyWeek);
  const [error, setError] = useState("");
  const invalid = week.some((day) => day.enabled && (!day.opens_at || !day.closes_at || day.opens_at >= day.closes_at));
  const load = () => {
    setState("loading");
    void getTechnicianSchedule(technician.id).then(({ schedule }) => {
      const next = emptyWeek();
      schedule.forEach(({ weekday, opens_at, closes_at }) => { if (weekday >= 1 && weekday <= 7) next[weekday - 1] = { enabled: true, opens_at: opens_at.slice(0, 5), closes_at: closes_at.slice(0, 5) }; });
      setWeek(next);
      setState("ready");
    }).catch(() => setState("load-error"));
  };
  useEffect(load, [technician.id]);
  const update = (index: number, patch: Partial<Day>) => { setWeek((days) => days.map((day, current) => current === index ? { ...day, ...patch } : day)); setState("ready"); };
  const save = async () => {
    if (invalid || state === "saving") return;
    setState("saving"); setError("");
    const schedule = week.flatMap((day, index) => day.enabled ? [{ weekday: index + 1, opens_at: day.opens_at, closes_at: day.closes_at }] : []);
    try { await saveTechnicianSchedule(technician.id, schedule); onSaved(formatTechnicianSchedule(schedule)); setState("saved"); }
    catch (cause) { setError(cause instanceof ApiError && cause.structuredDetail?.code === "invalid_schedule" ? "Revisa los horarios ingresados." : "No pudimos guardar el horario. Intenta nuevamente."); setState("error"); }
  };
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando horario" />;
  if (state === "load-error") return <div className="technician-schedule-editor__feedback"><StateMessage tone="danger" role="alert" title="No pudimos cargar el horario" detail="Intenta nuevamente para recuperar la disponibilidad." /><Button variant="secondary" onClick={load}>Reintentar</Button></div>;
  return <div className="technician-schedule-editor">
    <div className="technician-schedule-editor__days" aria-label="Días y horarios de atención">
      {week.map((day, index) => <div className="technician-schedule-editor__row" key={DAYS[index]}>
        <Button variant="secondary" className="technician-schedule-editor__day" aria-pressed={day.enabled} disabled={state === "saving"} onClick={() => update(index, { enabled: !day.enabled })}>{DAYS[index]}</Button>
        <Input label="Inicio" aria-label={`Inicio ${DAYS[index]}`} type="time" value={day.opens_at} disabled={!day.enabled || state === "saving"} onChange={(event) => update(index, { opens_at: event.target.value })} />
        <Input label="Fin" aria-label={`Fin ${DAYS[index]}`} type="time" value={day.closes_at} disabled={!day.enabled || state === "saving"} onChange={(event) => update(index, { closes_at: event.target.value })} />
      </div>)}
    </div>
    {invalid ? <StateMessage tone="danger" role="alert" title="El horario de fin debe ser posterior al de inicio." /> : null}
    {state === "saving" ? <StateMessage tone="info" role="status" spinner title="Guardando horario" /> : null}
    {state === "error" ? <StateMessage tone="danger" role="alert" title={error} /> : null}
    {state === "saved" ? <StateMessage tone="success" role="status" title="Horario guardado" /> : null}
    <Button className="technician-schedule-editor__save" disabled={state === "saving" || invalid} onClick={() => void save()}>{state === "saving" ? "Guardando…" : "Guardar horario"}</Button>
  </div>;
}
