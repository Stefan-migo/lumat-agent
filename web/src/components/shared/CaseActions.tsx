import { useState } from "react";
import type { UserRef } from "../../types";
import { Button } from "../primitives/Button";
import { Select } from "../primitives/Select";
import { caseStatusLabel } from "./toneMaps";

export interface CaseActionTarget {
  id: number;
  status: string;
  responsible_id: number | null;
  emergency: boolean;
  ack_by: string | null;
}

export const CASE_STATUSES = ["abierto", "en_evaluacion", "escalado", "cerrado"];

export function CaseActions({
  target,
  users,
  onUpdate,
  onAcknowledge,
}: {
  target: CaseActionTarget;
  users: UserRef[];
  onUpdate?: (caseId: number, status: string, responsibleId: number | null) => Promise<void>;
  onAcknowledge?: (caseId: number) => Promise<void>;
}) {
  const [status, setStatus] = useState(target.status);
  const [responsibleId, setResponsibleId] = useState(target.responsible_id === null ? "" : String(target.responsible_id));
  const [busy, setBusy] = useState(false);
  const emergencyUnanswered = target.emergency && target.ack_by === null;
  const run = async (action: (() => Promise<void>) | undefined) => {
    if (!action) return;
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cases-list__actions">
      <Select
        label="Estado"
        aria-label={`Estado caso ${target.id}`}
        value={status}
        onChange={(event) => setStatus(event.target.value)}
        options={CASE_STATUSES.map((value) => ({ value, label: caseStatusLabel(value) }))}
        size="sm"
      />
      <Select
        label="Responsable"
        aria-label={`Responsable caso ${target.id}`}
        value={responsibleId}
        onChange={(event) => setResponsibleId(event.target.value)}
        options={[{ value: "", label: "Sin asignar" }, ...users.map((user) => ({ value: String(user.id), label: user.username }))]}
        size="sm"
      />
      <div className="table__actions">
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => run(onUpdate ? () => onUpdate(target.id, status, responsibleId ? Number(responsibleId) : null) : undefined)}
        >
          Actualizar
        </Button>
        {emergencyUnanswered ? (
          <Button variant="secondary" disabled={busy} onClick={() => run(onAcknowledge ? () => onAcknowledge(target.id) : undefined)}>
            Reconocer
          </Button>
        ) : null}
      </div>
    </div>
  );
}
