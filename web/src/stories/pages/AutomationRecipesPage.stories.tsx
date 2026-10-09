import type { Meta, StoryObj } from '@storybook/react';
import { AutomationRecipesPage } from '../../components/pages/AutomationRecipesPage';
import type { AutomationInstallation, AutomationRecipe } from '../../types';

const recipes: AutomationRecipe[] = [{ recipe_id: 'booking-confirmation', name: 'Confirmación de reserva', description: 'Confirma una reserva a quien la solicitó.', category: 'Reservas', trigger_kind: 'event', event_type: 'appointment.booked', channel_allowed: ['whatsapp', 'email'], recipient_target: 'customer', content: 'Tu reserva está confirmada. Te esperamos en la fecha acordada.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'string', required: true, default: 'whatsapp' }] }];
const installations: AutomationInstallation[] = [{ id: 1, recipe_id: 'booking-confirmation', parameters: { channel: 'whatsapp' }, enabled: true, created_by: 'ana', created_at: null, updated_at: null }];
const loadRecipes = async () => ({ recipes });
const loadInstallations = async () => ({ installations });

const meta = {
  title: 'pages/AutomationRecipesPage',
  component: AutomationRecipesPage,
  parameters: { layout: 'fullscreen' },
} satisfies Meta<typeof AutomationRecipesPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { loadRecipes, loadInstallations } };
