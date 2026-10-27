import { useState } from "react";
import type { UserRef } from "../../types";
import { SearchInput } from "../primitives/SearchInput";
import { TechnicianScheduleEditor } from "../shared/TechnicianScheduleEditor";
import "./SettingsTechnicians.css";

export function SettingsTechnicians({ technicians }: { technicians: UserRef[] }) {
  const [selectedId, setSelectedId] = useState(technicians[0]?.id);
  const [visitedIds, setVisitedIds] = useState<number[]>(() => technicians[0] ? [technicians[0].id] : []);
  const [query, setQuery] = useState("");
  const selected = technicians.find((technician) => technician.id === selectedId);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const filteredTechnicians = technicians.filter((technician) => technician.username.toLocaleLowerCase().includes(normalizedQuery));
  const visitedTechnicians = technicians.filter((technician) => visitedIds.includes(technician.id));

  const selectTechnician = (technician: UserRef) => {
    setSelectedId(technician.id);
    setVisitedIds((current) => current.includes(technician.id) ? current : [...current, technician.id]);
  };

  return (
    <section className="settings-technicians" aria-label="Horarios de técnicos">
      <div className="settings-technicians__layout">
        <div className="settings-technicians__list">
          <SearchInput aria-label="Buscar técnico" placeholder="Buscar técnico" onSearch={setQuery} />
          {filteredTechnicians.length ? (
            <ul aria-label="Técnicos disponibles" className="settings-technicians__items">
              {filteredTechnicians.map((technician) => (
                <li key={technician.id}>
                  <button
                    type="button"
                    className="settings-technicians__option"
                    aria-pressed={technician.id === selectedId}
                    onClick={() => selectTechnician(technician)}
                  >
                    {technician.username}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="settings-technicians__no-results" role="status">No hay técnicos que coincidan con la búsqueda.</p>
          )}
        </div>

        <div className="settings-technicians__detail" aria-label="Disponibilidad del técnico seleccionado">
          {selected ? (
            <>
              <header className="settings-technicians__header">
                <h3>{selected.username}</h3>
                <p>Disponibilidad para visitas.</p>
              </header>
              <div className="settings-technicians__schedule-head" aria-hidden="true">
                <span>Día · Disponible</span><span>Inicio</span><span>Fin</span>
              </div>
              {visitedTechnicians.map((technician) => (
                <section
                  key={technician.id}
                  className="settings-technicians__editor"
                  hidden={technician.id !== selectedId}
                  aria-label={`Horario de ${technician.username}`}
                >
                  <TechnicianScheduleEditor technician={technician} onSaved={() => {}} />
                </section>
              ))}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
