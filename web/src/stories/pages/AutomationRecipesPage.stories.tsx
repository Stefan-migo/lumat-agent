import type { Meta, StoryObj } from '@storybook/react';
import { AutomationRecipesPage } from '../../components/pages/AutomationRecipesPage';
import type { AutomationInstallation, AutomationRecipe } from '../../types';

const descriptions = [
  'Envía un mensaje automático al confirmar una reserva.',
  'Notifica automáticamente al cancelar una visita.',
  'Informa automáticamente al reprogramar una visita.',
  'Envía un aviso automático al registrar una inasistencia.',
  'Notifica automáticamente al equipo al recibir una nueva solicitud.',
  'Solicita una evaluación automáticamente después de una visita.',
  'Envía un recordatorio automático según el intervalo configurado.',
  'Envía un resumen diario de la operación al administrador.',
  'Envía un resumen semanal de la operación al administrador.',
];
const recipeData = [
  ['appointment_confirmation', 'Confirmación de reserva', 'reservas', 'appointment.booked', 'whatsapp'],
  ['appointment_cancellation', 'Aviso de cancelación', 'reservas', 'appointment.cancelled', 'whatsapp'],
  ['appointment_rescheduled', 'Reprogramación de visita', 'reservas', 'appointment.rescheduled', 'whatsapp'],
  ['appointment_no_show', 'Aviso de no presentación', 'reservas', 'appointment.no_show', 'whatsapp'],
  ['case_new_request', 'Nueva solicitud al equipo', 'operacion', 'case.created', 'email'],
  ['appointment_review_request', 'Pedir evaluación', 'postventa', 'appointment.review_due', 'whatsapp'],
  ['customer_maintenance', 'Mantención periódica', 'postventa', 'customer.maintenance_due', 'whatsapp'],
  ['admin_daily_summary', 'Resumen diario', 'resumenes', 'admin.daily_summary_due', 'email'],
  ['admin_weekly_summary', 'Resumen semanal', 'resumenes', 'admin.weekly_summary_due', 'email'],
];
const recipes: AutomationRecipe[] = recipeData.map(([recipe_id, name, category, event_type, channel_allowed], index) => ({
  recipe_id, name, category, event_type, description: descriptions[index], trigger_kind: 'event', channel_allowed: [channel_allowed], recipient_target: 'customer', content: '', cooldown_seconds: 0,
  parameters: [{ key: 'channel', label: 'Canal', type: 'channel', required: true, default: channel_allowed }],
}));
const installations: AutomationInstallation[] = [{ id: 1, recipe_id: recipes[0].recipe_id, parameters: { channel: 'whatsapp' }, enabled: true, created_by: 'ana', created_at: null, updated_at: null }];
const loadRecipes = async () => ({ recipes });
const loadInstallations = async () => ({ installations });

const meta = { title: 'pages/AutomationRecipesPage', component: AutomationRecipesPage, parameters: { layout: 'fullscreen' } } satisfies Meta<typeof AutomationRecipesPage>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Catalog: Story = { args: { loadRecipes, loadInstallations: async () => ({ installations: [] }) } };
export const WithInstallations: Story = { args: { loadRecipes, loadInstallations } };
