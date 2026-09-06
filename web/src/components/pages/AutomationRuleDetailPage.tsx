import { useCallback, useEffect, useState } from "react";
import {
  createAutomationRule,
  disableAutomationRule,
  enableAutomationRule,
  getAutomationRule,
  updateAutomationRule,
} from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Rule, User } from "../../types";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

type RuleInput = Omit<Rule, "id" | "enabled" | "created_by" | "created_at" | "updated_at">;
type Confirmation = "enable" | "disable" | null;

export interface AutomationRuleDetailPageProps {
  ruleId?: number | null;
  user: User;
  data?: Rule | null;
  state?: AsyncDataState;
  onRetry?: () => void;
  onBack?: () => void;
}

const emptyRule: RuleInput = {
  name: "",
  event_type: "",
  conditions: {},
  channel: "",
  template_event: "",
  cooldown_seconds: 0,
};

function isScalar(value: unknown): value is string | number | boolean | null {
  return value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean";
}

function validate(input: RuleInput): Partial<Record<keyof RuleInput | "conditions", string>> {
  const errors: Partial<Record<keyof RuleInput | "conditions", string>> = {};
  if (!input.name.trim()) errors.name = "El nombre es obligatorio";
  if (!input.event_type.trim()) errors.event_type = "El evento es obligatorio";
  if (!input.channel.trim()) errors.channel = "El canal es obligatorio";
  if (!input.template_event.trim()) errors.template_event = "El contenido de notificación es obligatorio";
  if (!Number.isInteger(input.cooldown_seconds) || input.cooldown_seconds < 0 || input.cooldown_seconds > 2592000) {
    errors.cooldown_seconds = "El cooldown debe estar entre 0 y 2592000 segundos";
  }
  if (Object.keys(input.conditions).some((key) => !key.trim() || !isScalar(input.conditions[key]))) {
    errors.conditions = "Las condiciones deben ser un objeto plano de valores escalares";
  }
  return errors;
}

function inputFromRule(rule: Rule | null | undefined): RuleInput {
  if (!rule) return emptyRule;
  return {
    name: rule.name,
    event_type: rule.event_type,
    conditions: rule.conditions,
    channel: rule.channel,
    template_event: rule.template_event,
    cooldown_seconds: rule.cooldown_seconds,
  };
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "No se pudo completar la acción";
}

export function AutomationRuleDetailPage({ ruleId = null, user, data: controlledData, state: controlledState, onRetry, onBack }: AutomationRuleDetailPageProps) {
  const isCreate = ruleId === null || ruleId === undefined;
  const fetchRule = useCallback(() => getAutomationRule(ruleId as number).then((response) => response.rule), [ruleId]);
  const fetched = useAsyncData(fetchRule, !isCreate && controlledData === undefined);
  const [rule, setRule] = useState<Rule | null>(controlledData ?? null);
  const [form, setForm] = useState<RuleInput>(() => inputFromRule(controlledData));
  const [editing, setEditing] = useState(isCreate);
  const [confirmation, setConfirmation] = useState<Confirmation>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ReturnType<typeof validate>>({});
  const [mutating, setMutating] = useState(false);
  const fetchedRule = controlledData === undefined ? fetched.data : controlledData;
  const state = isCreate ? "ready" : controlledState ?? fetched.state;

  useEffect(() => {
    if (fetchedRule === undefined) return;
    setRule(fetchedRule);
    setForm(inputFromRule(fetchedRule));
  }, [fetchedRule]);

  const refresh = async () => {
    if (isCreate) return;
    const response = await getAutomationRule(ruleId);
    setRule(response.rule);
    setForm(inputFromRule(response.rule));
  };

  const save = async () => {
    const errors = validate(form);
    setValidationErrors(errors);
    if (Object.keys(errors).length > 0 || mutating) return;
    setMutating(true);
    setMutationError(null);
    try {
      if (isCreate) {
        const response = await createAutomationRule(form);
        setRule(response.rule);
        setForm(inputFromRule(response.rule));
        setEditing(false);
      } else {
        await updateAutomationRule(ruleId, form);
        await refresh();
        setEditing(false);
      }
    } catch (error) {
      setMutationError(errorMessage(error));
    } finally {
      setMutating(false);
    }
  };

  const changeStatus = async () => {
    if (!rule || !confirmation || mutating) return;
    setMutating(true);
    setMutationError(null);
    try {
      if (confirmation === "enable") await enableAutomationRule(rule.id);
      else await disableAutomationRule(rule.id);
      setConfirmation(null);
      await refresh();
    } catch (error) {
      setMutationError(errorMessage(error));
    } finally {
      setMutating(false);
    }
  };

  const updateField = <K extends keyof RuleInput>(field: K, value: RuleInput[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
    setValidationErrors((current) => ({ ...current, [field]: undefined }));
  };

  const retry = onRetry ?? fetched.retry;
  if (state === "loading") return <PageFrame title="Regla de automatización" state={<StateMessage tone="info" role="status" spinner title="Cargando regla" />}>{null}</PageFrame>;
  if (state === "denied") return <PageFrame title="Regla de automatización" state={<StateMessage tone="danger" role="alert" title="No tienes permiso para ver la regla" />}>{null}</PageFrame>;
  if (state === "error") return <PageFrame title="Regla de automatización" state={<div><StateMessage tone="danger" role="alert" title="No pudimos cargar la regla" /><button type="button" onClick={retry}>Reintentar</button></div>}>{null}</PageFrame>;
  if (!isCreate && !rule) return <PageFrame title="Regla de automatización" state={<StateMessage tone="danger" role="alert" title="Regla no encontrada" />}>{null}</PageFrame>;

  const readOnly = user.role !== "admin" || !editing;
  const title = isCreate ? "Nueva regla de automatización" : rule?.name || "Regla de automatización";
  return <PageFrame title={title} state={mutationError ? <StateMessage tone="danger" role="alert" title="No se pudo completar la acción" detail={mutationError} /> : undefined}>
    <div className="automation-rule-detail">
      {onBack ? <Button variant="secondary" onClick={onBack}>Volver a reglas</Button> : null}
      {!isCreate && rule ? <p>Estado: <strong>{rule.enabled ? "Habilitada" : "Deshabilitada"}</strong></p> : null}
      <form onSubmit={(event) => { event.preventDefault(); void save(); }}>
        <label htmlFor="automation-rule-name">Nombre</label>
        <input id="automation-rule-name" value={form.name} readOnly={readOnly} onChange={(event) => updateField("name", event.target.value)} aria-invalid={Boolean(validationErrors.name)} />
        {validationErrors.name ? <small role="alert">{validationErrors.name}</small> : null}
        <label htmlFor="automation-rule-event">Evento</label>
        <input id="automation-rule-event" value={form.event_type} readOnly={readOnly} onChange={(event) => updateField("event_type", event.target.value)} />
        {validationErrors.event_type ? <small role="alert">{validationErrors.event_type}</small> : null}
        <label htmlFor="automation-rule-conditions">Condiciones (JSON)</label>
        <textarea id="automation-rule-conditions" value={JSON.stringify(form.conditions)} readOnly={readOnly} onChange={(event) => { try { updateField("conditions", JSON.parse(event.target.value)); } catch { setValidationErrors((current) => ({ ...current, conditions: "Las condiciones deben ser JSON válido" })); } }} />
        {validationErrors.conditions ? <small role="alert">{validationErrors.conditions}</small> : null}
        <label htmlFor="automation-rule-channel">Canal</label>
        <input id="automation-rule-channel" value={form.channel} readOnly={readOnly} onChange={(event) => updateField("channel", event.target.value)} />
        {validationErrors.channel ? <small role="alert">{validationErrors.channel}</small> : null}
        <label htmlFor="automation-rule-template-event">Contenido de notificación</label>
        <input id="automation-rule-template-event" value={form.template_event} readOnly={readOnly} onChange={(event) => updateField("template_event", event.target.value)} />
        {validationErrors.template_event ? <small role="alert">{validationErrors.template_event}</small> : null}
        <label htmlFor="automation-rule-cooldown">Cooldown (segundos)</label>
        <input id="automation-rule-cooldown" type="number" value={form.cooldown_seconds} readOnly={readOnly} onChange={(event) => updateField("cooldown_seconds", Number(event.target.value))} />
        {validationErrors.cooldown_seconds ? <small role="alert">{validationErrors.cooldown_seconds}</small> : null}
        {user.role === "admin" && editing ? <Button type="submit" disabled={mutating}>{isCreate ? "Crear regla" : "Guardar cambios"}</Button> : null}
      </form>
      {user.role === "admin" && !isCreate && !editing ? <div>
        <Button onClick={() => setEditing(true)}>Editar regla</Button>
        <Button variant="secondary" onClick={() => setConfirmation(rule?.enabled ? "disable" : "enable")}>
          {rule?.enabled ? "Deshabilitar regla" : "Habilitar regla"}
        </Button>
      </div> : null}
    </div>
    <Dialog open={confirmation !== null} onClose={() => { if (!mutating) setConfirmation(null); }} title={confirmation === "enable" ? "Habilitar regla" : "Deshabilitar regla"}>
      <p>¿Confirmas este cambio de estado?</p>
      <Button disabled={mutating} onClick={() => void changeStatus()}>{confirmation === "enable" ? "Confirmar habilitación" : "Confirmar deshabilitación"}</Button>
    </Dialog>
  </PageFrame>;
}
