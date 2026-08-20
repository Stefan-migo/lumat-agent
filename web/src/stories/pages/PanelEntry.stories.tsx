import type { Meta, StoryObj } from "@storybook/react";
import { DashboardOverview } from "./Dashboard.stories";
import { PanelShell } from "../../components/domain/PanelShell";

const meta = {
  title: "pages/Panel Entry",
  component: PanelShell,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Storybook target for the authenticated Lumat entry layout. Desktop uses a compact 192px sidebar; tablet and mobile use a modal drawer opened from a compact brand/menu bar. The page owns its heading and actions, so the shell does not add a redundant desktop header. This design composes the current Dashboard story inside the production PanelShell promoted to `components/domain`.",
      },
    },
  },
} satisfies Meta<typeof PanelShell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DesktopAdmin: Story = {
  args: {
    user: { username: "ana", role: "admin" },
    currentView: "dashboard",
    children: <DashboardOverview />,
  },
  parameters: { viewport: { defaultViewport: "bp-lg" } },
};

export const DesktopOperator: Story = {
  args: {
    user: { username: "veronica", role: "operador" },
    currentView: "dashboard",
    children: <DashboardOverview />,
  },
  parameters: { viewport: { defaultViewport: "bp-lg" } },
};

export const TabletDrawerOpen: Story = {
  args: {
    user: { username: "ana", role: "admin" },
    currentView: "dashboard",
    drawerInitiallyOpen: true,
    children: <DashboardOverview />,
  },
  parameters: { viewport: { defaultViewport: "tablet-compact" } },
};

export const MobileDrawerOpen: Story = {
  args: {
    user: { username: "veronica", role: "operador" },
    currentView: "dashboard",
    drawerInitiallyOpen: true,
    children: <DashboardOverview />,
  },
  parameters: { viewport: { defaultViewport: "mobile-compact" } },
};

