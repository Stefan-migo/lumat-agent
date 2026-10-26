import type { Meta, StoryObj } from "@storybook/react";
import { Dashboard, type DashboardState as PageDashboardState } from "../../components/pages/Dashboard";
import type { DashboardToday, DashboardTrendBucket, Kpis } from "../../types";

export type DashboardState = PageDashboardState;

export interface DashboardOverviewProps {
  state?: DashboardState;
  data?: Kpis | null;
}

const MOCK_TODAY: DashboardToday = {
  tz: "America/Santiago",
  local_date: "2026-09-09",
  appointments_today: [
    { id: 11, service: "Instalación calefont", customer_name: "María José", local_start: "09:30", starts_at: "2026-09-09T12:30:00Z", ends_at: "2026-09-09T14:00:00Z" },
    { id: 12, service: "Mantencion preventiva", customer_name: "Pedro", local_start: "11:00", starts_at: "2026-09-09T14:00:00Z", ends_at: "2026-09-09T15:00:00Z" },
    { id: 13, service: "Reparación termo", customer_name: "Lucía", local_start: "15:30", starts_at: "2026-09-09T18:30:00Z", ends_at: "2026-09-09T19:30:00Z" },
  ],
  unanswered_conversations: [
    { id: 21, customer_name: "Andrés", last_message_at: "2026-09-09T14:20:00Z", state: "BOT" },
    { id: 22, customer_name: "Carla", last_message_at: "2026-09-09T15:05:00Z", state: "BOT" },
  ],
  urgent_cases: [
    { id: 31, customer_id: 12, conversation_id: 44, customer_name: "Rosa", service: "calefont", summary: "Fuga de agua en el calefont", emergency: true, escalated_at: "2026-09-09T13:00:00Z" },
  ],
};

const MOCK_TREND: DashboardTrendBucket[] = [
  { start: "2026-09-03", count: 6 },
  { start: "2026-09-04", count: 9 },
  { start: "2026-09-05", count: 4 },
  { start: "2026-09-06", count: 0 },
  { start: "2026-09-07", count: 11 },
  { start: "2026-09-08", count: 7 },
  { start: "2026-09-09", count: 12 },
];

const MOCK_KPIS: Kpis = {
  contacts: 1248,
  motivos: [["consulta", 34], ["visita", 12], ["calefont", 9], ["instalación", 5], ["garantía", 3]],
  derived: 18,
  visit_requests: 12,
  new_customers: 24,
  window_days: 7,
  window_start: "2026-09-03",
  trend: MOCK_TREND,
  today: MOCK_TODAY,
};

export function DashboardOverview({ state = "ready", data = MOCK_KPIS }: DashboardOverviewProps) {
  return <Dashboard data={data} state={state} />;
}

const meta = {
  title: "pages/Dashboard",
  parameters: { layout: "fullscreen" },
  excludeStories: ["DashboardOverview"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = { render: () => <DashboardOverview /> };
export const Desktop: Story = { ...Overview, parameters: { viewport: { width: 1280, height: 900 } } };
export const Tablet: Story = { ...Overview, parameters: { viewport: { width: 768, height: 1024 } } };
export const Mobile: Story = { ...Overview, parameters: { viewport: { width: 390, height: 844 } } };
export const Loading: Story = { render: () => <DashboardOverview state="loading" /> };
export const Empty: Story = { render: () => <DashboardOverview state="empty" /> };
export const Stale: Story = { render: () => <DashboardOverview state="stale" /> };
export const PartialError: Story = { render: () => <DashboardOverview state="partial-error" /> };
export const FatalError: Story = { render: () => <DashboardOverview state="fatal-error" /> };
