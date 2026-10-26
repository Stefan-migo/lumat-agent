import "./primitives.css";
import { WEEKDAY_NAMES } from "../shared/agendaTime";

export interface DayToggleProps {
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  label?: string;
}

export function DayToggle({ value, onChange, disabled = false, label = "Días de la semana" }: DayToggleProps) {
  return (
    <div className="day-toggle" role="group" aria-label={label}>
      {WEEKDAY_NAMES.map((day) => {
        const selected = value.includes(day);
        return (
          <button
            key={day}
            type="button"
            className="day-toggle__day"
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => onChange(selected ? value.filter((item) => item !== day) : [...value, day])}
          >
            {day}
          </button>
        );
      })}
    </div>
  );
}
