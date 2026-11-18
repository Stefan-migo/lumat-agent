import { useCallback, useEffect, useState } from "react";
import { ApiError, listPanelSessions, revokeAllPanelSessions, revokePanelSession } from "../../api";
import type { PanelSession } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { DataTable, type Column } from "../shared/DataTable";
import { StateMessage } from "../shared/StateMessage";
import { useToast } from "../primitives/Toast";

function deviceLabel(userAgent: string | null): string {
  if (!userAgent?.trim()) return "Dispositivo desconocido";

  const device = /iPhone/i.test(userAgent) ? "iPhone"
    : /iPad/i.test(userAgent) ? "iPad"
      : /Android/i.test(userAgent) ? "Android"
        : /Windows/i.test(userAgent) ? "Windows"
          : /Macintosh|Mac OS/i.test(userAgent) ? "Mac"
            : /Linux/i.test(userAgent) ? "Linux" : null;
  const browser = /Edg\//i.test(userAgent) ? "Edge"
    : /OPR\//i.test(userAgent) ? "Opera"
      : /Firefox\//i.test(userAgent) ? "Firefox"
        : /Chrome\//i.test(userAgent) ? "Chrome"
          : /Safari\//i.test(userAgent) ? "Safari" : null;

  if (!device && !browser) return "Dispositivo desconocido";
  return [device, browser].filter(Boolean).join(" · ") || "Dispositivo desconocido";
}

function shortDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("es-CL", {
    day: "numeric", month: "short", year: "numeric",
  }).format(date);
}

type ConfirmationTarget = { kind: "device"; session: PanelSession } | { kind: "others" };

export function PanelSessions() {
  const [sessions, setSessions] = useState<PanelSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [busyAll, setBusyAll] = useState(false);
  const [target, setTarget] = useState<ConfirmationTarget | null>(null);
  const toast = useToast();

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await listPanelSessions();
      setSessions(result.sessions);
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.detail : "Intenta nuevamente en unos minutos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const confirm = async () => {
    if (!target) return;
    const selected = target;
    setActionError(null);
    if (selected.kind === "device") setBusyId(selected.session.id);
    else setBusyAll(true);

    try {
      if (selected.kind === "device") await revokePanelSession(selected.session.id);
      else await revokeAllPanelSessions();
      setTarget(null);
      toast.show(selected.kind === "device" ? "Dispositivo revocado. El acceso se cerró." : "Se cerraron las demás sesiones.");
      await refresh();
    } catch (error) {
      setActionError(error instanceof ApiError ? error.detail : "No pudimos revocar el acceso. Intenta nuevamente.");
    } finally {
      setBusyId(null);
      setBusyAll(false);
    }
  };

  const columns: Column<PanelSession>[] = [
    { key: "device", header: "Dispositivo", render: (session) => <span className="panel-sessions__device">{deviceLabel(session.user_agent)}</span> },
    { key: "last-used", header: "Último uso", render: (session) => <time dateTime={session.last_used_at}>{shortDate(session.last_used_at)}</time> },
    { key: "status", header: "Estado", render: (session) => session.current ? <Badge tone="success">Este dispositivo</Badge> : <span aria-label="Otro dispositivo">—</span> },
  ];
  const selectedDevice = target?.kind === "device" ? deviceLabel(target.session.user_agent) : null;
  const anyBusy = busyId !== null || busyAll;

  return (
    <section className="panel-sessions" aria-label="Dispositivos">
      <Card
        title="Dispositivos"
        description="Cada dispositivo que abrió el panel conserva el acceso hasta que lo revoques."
        headerAction={<Button variant="danger" disabled={anyBusy || loading || sessions.length < 2} onClick={() => setTarget({ kind: "others" })}>Cerrar las demás sesiones</Button>}
      >
        {loading ? <StateMessage tone="info" role="status" spinner title="Cargando dispositivos" /> : null}
        {!loading && loadError ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los dispositivos" detail={loadError} /> : null}
        {!loading && !loadError ? <div className="panel-sessions__table"><DataTable
          columns={columns}
          rows={sessions}
          rowKey={(session) => String(session.id)}
          emptyMessage="No hay dispositivos recordados"
          actions={(session) => <Button variant="danger" disabled={anyBusy} onClick={() => setTarget({ kind: "device", session })}>Revocar</Button>}
        /></div> : null}
        {actionError ? <StateMessage tone="danger" role="alert" title="No pudimos completar la acción" detail={actionError} /> : null}
      </Card>

      <Dialog
        open={target !== null}
        onClose={() => { if (!anyBusy) setTarget(null); }}
        title={target?.kind === "others" ? "Cerrar las demás sesiones" : "Revocar dispositivo"}
        description={selectedDevice ? `Dispositivo: ${selectedDevice}` : undefined}
      >
        {target?.kind === "device" ? <p className="panel-sessions__confirmation">
          {target.session.current
            ? `Al revocar ${selectedDevice}, se cerrará el acceso y tendrás que ingresar tus credenciales de nuevo en este dispositivo.`
            : `Al revocar ${selectedDevice}, se cerrará el acceso y tendrás que ingresar tus credenciales de nuevo en ese dispositivo.`}
        </p> : <p className="panel-sessions__confirmation">Se cerrarán todas las sesiones excepto este dispositivo. En los demás dispositivos tendrán que ingresar sus credenciales de nuevo.</p>}
        <div className="dialog__actions">
          <Button variant="secondary" disabled={anyBusy} onClick={() => setTarget(null)}>Cancelar</Button>
          <Button variant="danger" disabled={anyBusy} onClick={() => void confirm()}>{target?.kind === "others" ? "Cerrar sesiones" : "Confirmar revocación"}</Button>
        </div>
      </Dialog>
    </section>
  );
}
