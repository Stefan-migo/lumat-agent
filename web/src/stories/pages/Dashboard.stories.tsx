import type { Meta, StoryObj } from "@storybook/react";
import { Dashboard } from "../../components/pages/Dashboard";
import type { AsyncDataState } from "../../hooks/useAsyncData";
import type { Kpis } from "../../types";

export type DashboardState = AsyncDataState | "stale" | "partial-error" | "fatal-error";

export interface DashboardOverviewProps {
  state?: DashboardState;
  data?: Kpis | null;
}

const MOCK_KPIS: Kpis = {
  contacts: 1248,
  motivos: [["consulta", 34], ["visita", 12]],
  derived: 18,
  visit_requests: 12,
  window_days: 7,
  window_start: "2026-08-18",
};

export function DashboardOverview({ state = "ready", data = MOCK_KPIS }: DashboardOverviewProps) {
  const normalized: AsyncDataState = state === "fatal-error" || state === "stale" || state === "partial-error" ? "error" : state;
  return <Dashboard data={data} state={normalized} />;
}

const meta = {
  title: "pages/Dashboard",
  parameters: { layout: "fullscreen" },
  excludeStories: ["DashboardOverview"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = { render: () => <DashboardOverview /> };
export const Loading: Story = { render: () => <DashboardOverview state="loading" /> };
export const Empty: Story = { render: () => <DashboardOverview state="empty" /> };
export const Stale: Story = { render: () => <DashboardOverview state="stale" /> };
export const PartialError: Story = { render: () => <DashboardOverview state="partial-error" /> };
export const FatalError: Story = { render: () => <DashboardOverview state="fatal-error" /> };
