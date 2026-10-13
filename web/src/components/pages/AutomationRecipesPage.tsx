import { useCallback, useMemo, useState } from 'react';
import { CalendarCheck, CalendarClock, CalendarDays, CalendarX, FileText, Info, Mail, MessageCircle, RefreshCw, Star, Timer, UserX, Wrench } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ApiError, createAutomationInstallation, disableAutomationInstallation, enableAutomationInstallation, listAutomationInstallations, listAutomationRecipes, updateAutomationInstallation } from '../../api';
import { useAsyncData } from '../../hooks/useAsyncData';
import type { AutomationInstallation, AutomationRecipe, AutomationInstallationsResponse, AutomationRecipesResponse } from '../../types';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Dialog } from '../primitives/Dialog';
import { Icon } from '../primitives/Icon';
import { Input } from '../primitives/Input';
import { SearchInput } from '../primitives/SearchInput';
import { Select } from '../primitives/Select';
import { Skeleton } from '../primitives/Skeleton';
import { Tabs } from '../primitives/Tabs';
import { EmptyState } from '../shared/EmptyState';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';
import './AutomationRecipesPage.css';

export interface AutomationRecipesPageProps {
  loadRecipes?: () => Promise<AutomationRecipesResponse>;
  loadInstallations?: () => Promise<AutomationInstallationsResponse>;
}

const categories: Record<string, { label: string; icon: LucideIcon }> = {
  reservas: { label: 'Reservas', icon: CalendarCheck },
  operacion: { label: 'Operación', icon: Wrench },
  postventa: { label: 'Postventa', icon: Star },
  resumenes: { label: 'Resúmenes', icon: CalendarDays },
};

const recipeIcons: Record<string, LucideIcon> = {
  appointment_confirmation: CalendarCheck,
  appointment_cancellation: CalendarX,
  appointment_rescheduled: RefreshCw,
  appointment_no_show: UserX,
  case_new_request: FileText,
  appointment_review_request: Star,
  customer_maintenance: Wrench,
  admin_daily_summary: CalendarClock,
  admin_weekly_summary: CalendarDays,
};

const weekdayOptions = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map((label, index) => ({ value: String(index + 1), label }));
const channelLabel: Record<string, string> = { whatsapp: 'WhatsApp', email: 'Email' };
const channelIcon: Record<string, LucideIcon> = { whatsapp: MessageCircle, email: Mail };

function initialParameters(recipe: AutomationRecipe, installation?: AutomationInstallation) {
  return Object.fromEntries(recipe.parameters.map((parameter) => {
    if (installation && parameter.key in installation.parameters) return [parameter.key, installation.parameters[parameter.key]];
    return [parameter.key, parameter.key === 'channel'
      ? recipe.channel_allowed.includes(String(parameter.default)) ? parameter.default : recipe.channel_allowed[0] ?? ''
      : parameter.default ?? ''];
  }));
}

function parameterSummary(parameters: Record<string, unknown>, recipe?: AutomationRecipe) {
  return Object.entries(parameters).map(([key, value]) => {
    const label = recipe?.parameters.find((parameter) => parameter.key === key)?.label ?? key;
    const display = key === 'channel' ? channelLabel[String(value)] ?? String(value)
      : key === 'weekday' ? weekdayOptions.find((option) => option.value === String(value))?.label ?? String(value)
        : String(value);
    return `${label}: ${display}`;
  }).join(' · ');
}

export function AutomationRecipesPage({ loadRecipes: fetchRecipes = listAutomationRecipes, loadInstallations: fetchInstallations = listAutomationInstallations }: AutomationRecipesPageProps) {
  const [refresh, setRefresh] = useState(0);
  const [activeTab, setActiveTab] = useState('catalog');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<{ recipe: AutomationRecipe; installation?: AutomationInstallation } | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [pending, setPending] = useState<string | number | null>(null);
  const [actionError, setActionError] = useState('');
  const loadRecipes = useCallback(() => fetchRecipes(), [fetchRecipes]);
  const loadInstallations = useCallback(() => fetchInstallations(), [fetchInstallations]);
  const recipes = useAsyncData(loadRecipes);
  const installations = useAsyncData(loadInstallations, true, refresh);
  const recipeList = recipes.data?.recipes ?? [];
  const installationList = installations.data?.installations ?? [];
  const installedByRecipe = new Map(installationList.map((item) => [item.recipe_id, item]));
  const categoryOptions = useMemo(() => [...new Set(recipeList.map((recipe) => recipe.category))].map((slug) => ({ value: slug, label: categories[slug]?.label ?? slug })), [recipeList]);
  const filteredRecipes = recipeList.filter((recipe) => {
    const query = search.trim().toLocaleLowerCase();
    return (selectedCategory === 'all' || recipe.category === selectedCategory)
      && (!query || `${recipe.name} ${recipe.description} ${recipe.category}`.toLocaleLowerCase().includes(query));
  });
  const run = async (key: string | number, action: () => Promise<unknown>) => {
    setPending(key); setActionError('');
    try { await action(); setSelected(null); setRefresh((value) => value + 1); }
    catch (error) { setActionError(error instanceof ApiError ? error.detail : 'No pudimos guardar los cambios.'); }
    finally { setPending(null); }
  };
  const stateBlock = (state: string, retry: () => void, label: string) => state === 'loading'
    ? <div className="automation-recipes__loading" role="status" aria-label={`Cargando ${label}`}><Skeleton height="3rem" /><Skeleton height="3rem" /></div>
    : state === 'denied' ? <StateMessage tone="warning" role="alert" title="No tienes permiso para ver estas automatizaciones" />
      : state === 'error' ? <div className="automation-recipes__load-error"><StateMessage tone="danger" role="alert" title={`No pudimos cargar ${label}`} /><Button variant="secondary" onClick={retry}>Reintentar</Button></div> : null;
  const openConfiguration = (recipe: AutomationRecipe, installation?: AutomationInstallation) => {
    setSelected({ recipe, installation });
    setParameters(initialParameters(recipe, installation));
    setActionError('');
  };
  const submitConfiguration = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    const { recipe, installation } = selected;
    void run(installation?.id ?? recipe.recipe_id, () => installation
      ? updateAutomationInstallation(installation.id, parameters)
      : createAutomationInstallation(recipe.recipe_id, parameters));
  };
  const showEmptyInstallBanner = installations.state === 'ready' && installationList.length === 0;

  return <PageFrame
    title="Automatizaciones"
    subtitle="Mensajes automáticos para cada etapa de la atención."
    headerClassName="automation-recipes__header"
    actions={<Button variant="secondary" onClick={() => setActiveTab('installed')}>Ver instaladas <span className="automation-recipes__count">{installationList.length}</span></Button>}
    state={showEmptyInstallBanner ? <div className="automation-recipes__empty-banner"><Icon icon={Timer} /><StateMessage tone="info" role="status" title="Aún no tienes automatizaciones instaladas." detail="Elige una plantilla para comenzar." /></div> : undefined}
    className="automation-recipes"
  >
    {actionError ? <StateMessage tone="danger" role="alert" title="No se guardaron los cambios" detail={actionError} /> : null}
    {recipes.state === 'denied' ? stateBlock(recipes.state, recipes.retry, 'el catálogo') : null}
    {installations.state === 'denied' ? stateBlock(installations.state, installations.retry, 'las instalaciones') : null}
    {recipes.state === 'error' ? stateBlock(recipes.state, recipes.retry, 'el catálogo') : null}
    {installations.state === 'error' ? stateBlock(installations.state, installations.retry, 'las instalaciones') : null}
    <Tabs
      ariaLabel="Secciones de automatizaciones"
      activeTab={activeTab}
      onTabChange={setActiveTab}
      tabs={[{ id: 'catalog', label: `Catálogo (${recipeList.length})` }, { id: 'installed', label: `Instaladas (${installationList.length})` }]}
    >
      {(tab) => tab === 'catalog' ? <>
        {recipes.state === 'loading' ? stateBlock(recipes.state, recipes.retry, 'el catálogo') : null}
        {recipes.state === 'ready' && recipeList.length === 0 ? <EmptyState title="No hay plantillas disponibles" description="El catálogo de automatizaciones está vacío." /> : null}
        {recipes.state === 'ready' && recipeList.length > 0 ? <>
          <div className="automation-recipes__toolbar">
            <SearchInput aria-label="Buscar automatización" placeholder="Buscar automatización…" delay={0} onSearch={setSearch} />
            <Select label="Categoría" aria-label="Categoría" value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)} options={[{ value: 'all', label: 'Todas las categorías' }, ...categoryOptions]} />
          </div>
          <section className="automation-recipes__panel" aria-labelledby="automation-recipes-catalog-title">
            <h2 id="automation-recipes-catalog-title" className="automation-recipes__panel-title">Plantillas disponibles</h2>
            {filteredRecipes.length ? <div className="automation-recipes__rows">{filteredRecipes.map((recipe) => {
              const installation = installedByRecipe.get(recipe.recipe_id);
              const category = categories[recipe.category] ?? { label: recipe.category, icon: Info };
              return <article className="automation-recipes__row" key={recipe.recipe_id}>
                <span className="automation-recipes__recipe-icon"><Icon icon={recipeIcons[recipe.recipe_id] ?? Timer} /></span>
                <div className="automation-recipes__recipe-copy"><h3>{recipe.name}</h3><p>{recipe.description}</p></div>
                <div className="automation-recipes__chips">
                  <span className="automation-recipes__chip"><Icon icon={category.icon} size="sm" />{category.label}</span>
                  {recipe.channel_allowed.map((channel) => <span className="automation-recipes__chip" key={channel}><Icon icon={channelIcon[channel] ?? MessageCircle} size="sm" />{channelLabel[channel] ?? channel}</span>)}
                </div>
                {installation ? <><Badge tone="success" className="automation-recipes__installed-badge">Instalada</Badge><Button variant="secondary" disabled={pending !== null} onClick={() => openConfiguration(recipe, installation)}>Editar</Button></>
                  : <Button variant="secondary" disabled={pending !== null || installations.state !== 'ready'} onClick={() => openConfiguration(recipe)}>+ Configurar</Button>}
              </article>;
            })}</div> : <EmptyState title="No encontramos automatizaciones" description="Prueba con otro término o categoría." />}
            <p className="automation-recipes__footer"><Icon icon={Info} size="sm" />Configura el mensaje antes de activar la automatización.</p>
          </section>
        </> : null}
      </> : <>
        {installations.state === 'loading' ? stateBlock(installations.state, installations.retry, 'las automatizaciones instaladas') : null}
        {installations.state === 'ready' && installationList.length === 0 ? <EmptyState title="Aún no hay automatizaciones instaladas" description="Elige una plantilla del catálogo para comenzar." /> : null}
        {installations.state === 'ready' && installationList.length > 0 ? <section className="automation-recipes__panel" aria-label="Automatizaciones instaladas">
          <div className="automation-recipes__rows">{installationList.map((installation) => {
            const recipe = recipeList.find((candidate) => candidate.recipe_id === installation.recipe_id);
            return <article className="automation-recipes__row automation-recipes__installed-row" key={installation.id}>
              <div className="automation-recipes__recipe-copy"><h3>{recipe?.name ?? installation.recipe_id}</h3><p>{parameterSummary(installation.parameters, recipe) || 'Sin parámetros configurados'}</p></div>
              <Badge tone={installation.enabled ? 'success' : 'neutral'}>{installation.enabled ? 'Activa' : 'Inactiva'}</Badge>
              <Button variant="secondary" disabled={pending !== null} onClick={() => void run(installation.id, () => installation.enabled ? disableAutomationInstallation(installation.id) : enableAutomationInstallation(installation.id))}>{pending === installation.id ? 'Guardando…' : installation.enabled ? 'Desactivar' : 'Activar'}</Button>
              {recipe ? <Button variant="secondary" disabled={pending !== null} onClick={() => openConfiguration(recipe, installation)}>Editar</Button> : null}
            </article>;
          })}</div>
        </section> : null}
      </>}
    </Tabs>
    <Dialog open={selected !== null} onClose={() => setSelected(null)} title={selected ? `${selected.installation ? 'Editar' : 'Configurar'} ${selected.recipe.name}` : 'Configurar automatización'} description="Revisa los parámetros antes de activar la automatización." icon={selected ? recipeIcons[selected.recipe.recipe_id] ?? Timer : undefined} variant="sheet">
      {selected ? <form className="automation-recipes__form" onSubmit={submitConfiguration}>
        {selected.recipe.parameters.map((parameter) => parameter.key === 'channel' ? <Select key={parameter.key} label={parameter.label} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: event.target.value }))} options={selected.recipe.channel_allowed.map((value) => ({ value, label: channelLabel[value] ?? value }))} /> : parameter.type === 'weekday' ? <Select key={parameter.key} label={parameter.label} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: Number(event.target.value) }))} options={weekdayOptions} /> : <Input key={parameter.key} label={parameter.label} type={parameter.type === 'time' ? 'time' : parameter.type === 'number' ? 'number' : 'text'} required={parameter.required} value={String(parameters[parameter.key] ?? '')} disabled={pending !== null} onChange={(event) => setParameters((current) => ({ ...current, [parameter.key]: parameter.type === 'number' ? Number(event.target.value) : event.target.value }))} />)}
        <div className="automation-recipes__dialog-actions"><Button type="submit" disabled={pending !== null}>{pending ? selected.installation ? 'Guardando…' : 'Configurando…' : selected.installation ? 'Guardar cambios' : 'Configurar'}</Button><Button type="button" variant="secondary" disabled={pending !== null} onClick={() => setSelected(null)}>Cancelar</Button></div>
      </form> : null}
    </Dialog>
  </PageFrame>;
}
