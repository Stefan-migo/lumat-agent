import { CalendarDays, Check, CircleCheck, ClipboardCheck, Clock3, Headphones, MessageCircle, RotateCw, Sparkles, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import type { Customer, CustomerState } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { customerStateLabel, customerStateTone } from "./toneMaps";
import "./ChangeCustomerStateDialog.css";

export interface ChangeCustomerStateDialogProps {
  open: boolean;
  onClose: () => void;
  customer: Customer;
  subtitle: ReactNode;
  selectedState: CustomerState | null;
  onSelect: (state: CustomerState) => void;
  onSave: () => void;
  busy: boolean;
  feedback?: ReactNode;
}

const stateIcons = { nuevo: Sparkles, contactado: MessageCircle, pendiente: Clock3, agendado: CalendarDays, en_evaluacion: ClipboardCheck, finalizado: CircleCheck, cancelado: XCircle, postventa: Headphones };

export function ChangeCustomerStateDialog({ open, onClose, customer, subtitle, selectedState, onSelect, onSave, busy, feedback }: ChangeCustomerStateDialogProps) {
  const transitions = customer.allowed_transitions ?? [];
  return <Dialog open={open} onClose={onClose} title="Cambiar estado del cliente" icon={RotateCw} description="Selecciona el nuevo estado de atención.">
    <div className="change-state-dialog">
      <div className="change-state-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>{subtitle}</span></div><div className="change-state-dialog__current"><span>Estado actual</span><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></div></div>
      <h3>Nuevo estado</h3>
      {transitions.length ? <div className="change-state-dialog__options" role="radiogroup" aria-label="Nuevo estado">{transitions.map((value) => { const StateIcon = stateIcons[value]; return <Button key={value} type="button" role="radio" aria-checked={selectedState === value} variant="secondary" disabled={busy} className={selectedState === value ? "change-state-dialog__option is-selected" : "change-state-dialog__option"} onClick={() => onSelect(value)}><StateIcon /><span>{customerStateLabel(value)}</span><span className="change-state-dialog__radio" /></Button>; })}</div> : <p role="status">Este cliente no tiene transiciones de estado disponibles.</p>}
      {transitions.length ? <div className="change-state-dialog__transition"><span>Cambio:</span><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge><span aria-hidden="true">→</span><Badge tone={customerStateTone(selectedState ?? customer.state)}>{customerStateLabel(selectedState ?? customer.state)}</Badge></div> : null}
      {feedback}
      <footer><Button variant="secondary" onClick={onClose}>Cancelar</Button>{transitions.length ? <Button onClick={onSave} disabled={busy || !selectedState}><Check />{busy ? "Guardando…" : "Guardar estado"}</Button> : null}</footer>
    </div>
  </Dialog>;
}
