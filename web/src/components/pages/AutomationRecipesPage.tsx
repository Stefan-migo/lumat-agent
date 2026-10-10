import { useCallback, useState } from 'react';
import { ApiError, createAutomationInstallation, disableAutomationInstallation, enableAutomationInstallation, listAutomationInstallations, listAutomationRecipes } from '../../api';
import { useAsyncData } from '../../hooks/useAsyncData';
import type { AutomationInstallation, AutomationRecipe, AutomationInstallationsResponse, AutomationRecipesResponse } from '../../types';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Select } from '../primitives/Select';
import { Input } from '../primitives/Input';
import { EmptyState } from '../shared/EmptyState';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';

export interface AutomationRecipesPageProps {
  loadRecipes?: () => Promise<AutomationRecipesResponse>;
  loadInstallations?: () => Promise<AutomationInstallationsResponse>;
}

export function AutomationRecipesPage({ loadRecipes: fetchRecipes = listAutomationRecipes, loadInstallations: fetchInstallations = listAutomationInstallations }: AutomationRecipesPageProps) {
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<AutomationRecipe | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [pending, setPending] = useState<string | number | null>(null);
  const [actionError, setActionError] = useState('');
  const loadRecipes = useCallback(() => fetchRecipes(), [fetchRecipes]);
  const loadInstallations = useCallback(() => fetchInstallations(), [fetchInstallations]);
  const recipes = useAsyncData(loadRecipes);
  const installations = useAsyncData(loadInstallations, true, refresh);
  const installedByRecipe = new Map((installations.data?.installations ?? []).map((item) => [item.recipe_id, item]));
  const run = async (key: string | number, action: () => Promise<unknown>) => {
    setPending(key); setActionError('');
    try { await action(); setSelected(null); setRefresh((value) => value + 1); }
    catch (error) { setActionError(error instanceof ApiError ? error.detail : 'No pudimos guardar los cambios.'); }
    finally { setPending(null); }
  };
  const stateBlock = (state: string, retry: () => void, denied: boolean, label: string) => state === 'loading'
    ? <StateMessage tone="info" role="status" spinner title={`Cargando ${label}`} />
    : denied ? <StateMessage tone="warning" role="alert" title="No tienes permiso para ver estas automatizaciones" />
      : state === 'error' ? <><StateMessage tone="danger" role="alert" title={`No pudimos cargar ${label}`} /><Button variant="secondary" onClick={retry}>Reintentar</Button></> : null;
  return <PageFrame title="Automatizaciones" meta="Recetas disponibles para tu equipo">
    {actionError ? <StateMessage tone="danger" role="alert" title="No se guardaron los cambios" detail={actionError} /> : null}
    <h2>Catálogo de recetas</h2>
    {stateBlock(recipes.state, recipes.retry, recipes.state === 'denied', 'el catálogo')}
    {recipes.state === 'ready' && recipes.data?.recipes.length === 0 ? <StateMessage tone="danger" role="alert" title="El catálogo de recetas está vacío" detail="No hay recetas disponibles en el catálogo actualmente." /> : null}
    {recipes.data?.recipes.map((recipe) => {
      const installation = installedByRecipe.get(recipe.recipe_id);
      return <Card key={recipe.recipe_id} title={recipe.name}>
        <p>{recipe.category}</p><p>{recipe.description}</p><blockquote>{recipe.content}</blockquote>
        <p>Canales: {recipe.channel_allowed.join(', ')}</p>
        {installation ? <p>{installation.enabled ? 'Activa' : 'Inactiva'}</p> : <Button disabled={pending !== null || installations.state !== 'ready' || recipes.state !== 'ready'} onClick={() => { setSelected(recipe); setParameters(Object.fromEntries(recipe.parameters.map((parameter) => [parameter.key, parameter.key === 'channel' ? recipe.channel_allowed.includes(String(parameter.default)) ? parameter.default : recipe.channel_allowed[0] ?? '' : parameter.default ?? '']))); }}>Instalar</Button>}
      </Card>;
    })}
    {selected ? <Card title={`Instalar ${selected.name}`}><form onSubmit={(event) => { event.preventDefault(); void run(selected.recipe_id, () => createAutomationInstallation(selected.recipe_id, parameters)); }}>
      {selected.parameters.map((parameter) => parameter.key === 'channel' ? <Select key={parameter.key} label={parameter.label} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: event.target.value }))} options={selected.channel_allowed.map((value) => ({ value, label: value }))} /> : parameter.type === 'weekday' ? <Select key={parameter.key} label={parameter.label} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: Number(event.target.value) }))} options={['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map((label, index) => ({ value: String(index + 1), label }))} /> : <Input key={parameter.key} label={parameter.label} type={parameter.type === 'time' ? 'time' : parameter.type === 'number' ? 'number' : 'text'} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: parameter.type === 'number' ? Number(event.target.value) : event.target.value }))} />)}
      <Button type="submit" disabled={pending !== null}>{pending === selected.recipe_id ? 'Instalando…' : 'Confirmar instalación'}</Button><Button type="button" variant="secondary" disabled={pending !== null} onClick={() => setSelected(null)}>Cancelar</Button>
    </form></Card> : null}
    <h2>Recetas instaladas</h2>
    {stateBlock(installations.state, installations.retry, installations.state === 'denied', 'las recetas instaladas')}
    {installations.state === 'ready' && installations.data?.installations.length === 0 ? <EmptyState title="Aún no hay recetas instaladas" description="Instala una receta del catálogo para comenzar." /> : null}
    {installations.data?.installations.map((item: AutomationInstallation) => {
      const recipe = recipes.data?.recipes.find((candidate) => candidate.recipe_id === item.recipe_id);
      return <Card key={item.id} title={recipe?.name ?? item.recipe_id}><p>{Object.entries(item.parameters).map(([key, value]) => `${key}: ${String(value)}`).join(', ')}</p>
        <Button disabled={pending !== null} onClick={() => void run(item.id, () => item.enabled ? disableAutomationInstallation(item.id) : enableAutomationInstallation(item.id))}>{pending === item.id ? 'Guardando…' : item.enabled ? 'Desactivar' : 'Activar'}</Button>
      </Card>;
    })}
  </PageFrame>;
}
