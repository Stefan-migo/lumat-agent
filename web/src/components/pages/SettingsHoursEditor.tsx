import { useState } from "react";
import { Globe2, Pencil, Trash2, Users } from "lucide-react";
import type { Settings } from "../../types";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { DayToggle } from "../primitives/DayToggle";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { WEEKDAY_NAMES } from "../shared/agendaTime";
import "./SettingsHoursEditor.css";

type HoursData = Settings["hours"];
type Schedule = HoursData["schedule"][number];
type ScheduleEditor = { index: number | null; days: string[]; open: string; close: string };
const TIMEZONES = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];

function toDayNumbers(days: string[]) {
  return days.map((day) => WEEKDAY_NAMES.indexOf(day) + 1).filter((day) => day > 0).sort((a, b) => a - b);
}

function toDayNames(days: number[]) {
  return days.map((day) => WEEKDAY_NAMES[day - 1]).filter((day): day is string => Boolean(day));
}

function validSchedule(days: string[], open: string, close: string, occupied: Set<string>) {
  return days.length > 0 && days.every((day) => !occupied.has(day)) && Boolean(open) && Boolean(close) && open < close;
}

export interface SettingsHoursEditorProps {
  hours: HoursData;
  onChange: (hours: HoursData) => void;
}

export function SettingsHoursEditor({ hours, onChange }: SettingsHoursEditorProps) {
  const [editor, setEditor] = useState<ScheduleEditor | null>(null);
  const usedDays = new Set(hours.schedule.flatMap(({ days }) => toDayNames(days)));
  const timezoneOptions = [...new Set([hours.timezone, ...TIMEZONES])]
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right));

  const openEditor = (index: number | null) => {
    const schedule = index === null ? null : hours.schedule[index];
    setEditor({
      index,
      days: schedule ? toDayNames(schedule.days) : [],
      open: schedule?.open ?? "09:00",
      close: schedule?.close ?? "18:00",
    });
  };

  const occupiedForEditor = (index: number | null) => new Set(
    hours.schedule.flatMap((schedule, scheduleIndex) => scheduleIndex === index ? [] : toDayNames(schedule.days)),
  );

  const confirmEditor = () => {
    if (!editor || !validSchedule(editor.days, editor.open, editor.close, occupiedForEditor(editor.index))) return;
    const schedule: Schedule = { days: toDayNumbers(editor.days), open: editor.open, close: editor.close };
    const nextSchedule = editor.index === null
      ? [...hours.schedule, schedule]
      : hours.schedule.map((entry, index) => index === editor.index ? schedule : entry);
    onChange({ ...hours, schedule: nextSchedule });
    setEditor(null);
  };

  const updateTime = (index: number, field: "open" | "close", value: string) => {
    const schedule = hours.schedule[index];
    const next = { ...schedule, [field]: value };
    if (!next.days.length || !next.open || !next.close || next.open >= next.close) return;
    onChange({ ...hours, schedule: hours.schedule.map((entry, row) => row === index ? next : entry) });
  };

  return (
    <Card
      className="settings-hours-editor"
      title="Horarios de atención"
      description="Define cuándo atiende tu equipo."
      icon={Users}
      headerAction={(
        <div className="settings-hours-editor__timezone">
          <Globe2 aria-hidden="true" />
          <Select
            label="Zona horaria"
            size="sm"
            value={hours.timezone}
            onChange={(event) => onChange({ ...hours, timezone: event.target.value })}
            options={timezoneOptions.map((timezone) => ({ value: timezone, label: timezone }))}
          />
        </div>
      )}
    >
      <div className="settings-hours-editor__table-wrap" role="region" aria-label="Tabla de horarios" tabIndex={0}>
        <table className="settings-hours-editor__table" aria-label="Horarios de atención">
          <thead>
            <tr><th scope="col">Días</th><th scope="col">Inicio</th><th scope="col">Fin</th><th scope="col">Acciones</th></tr>
          </thead>
          <tbody>
            {hours.schedule.map((schedule, index) => editor?.index === index ? (
              <tr key={`schedule-${index}`} className="settings-hours-editor__edit-row">
                <td colSpan={4}>
                  <div className="settings-hours-editor__form">
                    <DayToggle
                      label={`Días de atención horario ${index + 1}`}
                      value={editor.days}
                      onChange={(days) => setEditor({ ...editor, days: days.filter((day) => !occupiedForEditor(index).has(day)) })}
                    />
                    <div className="settings-hours-editor__times">
                      <Input label={`Inicio horario ${index + 1}`} type="time" size="sm" value={editor.open} onChange={(event) => setEditor({ ...editor, open: event.target.value })} />
                      <Input label={`Fin horario ${index + 1}`} type="time" size="sm" value={editor.close} onChange={(event) => setEditor({ ...editor, close: event.target.value })} />
                    </div>
                    <div className="settings-hours-editor__form-actions">
                      <Button variant="tertiary" onClick={() => setEditor(null)}>Cancelar</Button>
                      <Button variant="secondary" aria-label="Confirmar horario" disabled={!validSchedule(editor.days, editor.open, editor.close, occupiedForEditor(index))} onClick={confirmEditor}>Confirmar</Button>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={`schedule-${index}`}>
                <td>{toDayNames(schedule.days).join(", ") || "Sin días seleccionados"}</td>
                <td><Input label={`Inicio horario ${index + 1}`} type="time" size="sm" value={schedule.open} onChange={(event) => updateTime(index, "open", event.target.value)} /></td>
                <td><Input label={`Fin horario ${index + 1}`} type="time" size="sm" value={schedule.close} onChange={(event) => updateTime(index, "close", event.target.value)} /></td>
                <td>
                  <div className="settings-hours-editor__row-actions">
                    <Button variant="tertiary" aria-label={`Editar días horario ${index + 1}`} onClick={() => openEditor(index)}><Pencil aria-hidden="true" /></Button>
                    <Button variant="tertiary" aria-label={`Eliminar horario ${index + 1}`} onClick={() => onChange({ ...hours, schedule: hours.schedule.filter((_, row) => row !== index) })}><Trash2 aria-hidden="true" /></Button>
                  </div>
                </td>
              </tr>
            ))}
            {(() => {
              const unassigned = WEEKDAY_NAMES.filter((day) => !usedDays.has(day));
              return unassigned.length ? <tr className="settings-hours-editor__unassigned" key="unassigned">
                <td>{unassigned.map((day) => WEEKDAY_NAMES[WEEKDAY_NAMES.indexOf(day)]).join(", ")}</td>
                <td colSpan={3}>Sin horario</td>
              </tr> : null;
            })()}
          </tbody>
        </table>
      </div>
      {editor?.index === null ? (
        <div className="settings-hours-editor__form settings-hours-editor__new-form">
          <DayToggle
            label="Días de atención"
            value={editor.days}
            onChange={(days) => setEditor({ ...editor, days: days.filter((day) => !usedDays.has(day)) })}
          />
          <div className="settings-hours-editor__times">
            <Input label="Inicio" type="time" size="sm" value={editor.open} onChange={(event) => setEditor({ ...editor, open: event.target.value })} />
            <Input label="Fin" type="time" size="sm" value={editor.close} onChange={(event) => setEditor({ ...editor, close: event.target.value })} />
          </div>
          <div className="settings-hours-editor__form-actions">
            <Button variant="tertiary" onClick={() => setEditor(null)}>Cancelar</Button>
            <Button variant="secondary" aria-label="Agregar horario" disabled={!validSchedule(editor.days, editor.open, editor.close, usedDays)} onClick={confirmEditor}>Confirmar</Button>
          </div>
        </div>
      ) : null}
      {editor === null ? <Button variant="tertiary" className="settings-hours-editor__add" aria-label="Agregar horario" onClick={() => openEditor(null)}>+ Agregar horario</Button> : null}
    </Card>
  );
}
