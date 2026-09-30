import type { Meta, StoryObj } from "@storybook/react";
import { DashboardOverview } from "./Dashboard.stories";
import { PanelShell } from "../../components/domain/PanelShell";

/** The footer account options only render when a logout handler exists, so stories supply one: without it the
 *  prop-dependent chrome is invisible to the rendered review. */
const onLogout = () => undefined;

const meta = {
  title: "pages/Panel Entry",
  component: PanelShell,
  parameters: {
    layout: "fullscreen",
    panelShell: false,
    docs: {
      description: {
        component:
          "Storybook target for the authenticated Lumat entry layout. Desktop uses a compact 192px sidebar; tablet and mobile use a modal drawer opened from a compact brand/menu bar. The shell renders a panel header (current view label) above the content area; the sidebar brand and the panel header share the same height, but the brand is dark green (`--corp-primary`) while the panel header is white (`--corp-surface`). The page still owns its own PageHeader for content context. This design composes the current Dashboard story inside the production PanelShell promoted to `components/domain`.",
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
    onLogout,
  },
  parameters: { viewport: { width: 1280, height: 900 } },
};

export const DesktopExpanded1024: Story = {
  ...DesktopAdmin,
  parameters: { viewport: { width: 1024, height: 900 } },
};

export const DesktopExpanded1280: Story = {
  ...DesktopAdmin,
  parameters: { viewport: { width: 1280, height: 900 } },
};

export const DesktopCollapsed1280: Story = {
  ...DesktopExpanded1280,
  play: async ({ canvasElement }) => {
    canvasElement.querySelector<HTMLButtonElement>(".panel-shell__collapse-button")?.click();
  },
};

export const DesktopOperator: Story = {
  args: {
    user: { username: "veronica", role: "operador" },
    currentView: "dashboard",
    children: <DashboardOverview />,
  },
  parameters: { viewport: { width: 1280, height: 900 } },
};

export const TabletDrawerOpen: Story = {
  args: {
    user: { username: "ana", role: "admin" },
    currentView: "dashboard",
    drawerInitiallyOpen: true,
    children: <DashboardOverview />,
    onLogout,
  },
  parameters: { viewport: { width: 768, height: 900 } },
};

export const TabletRail: Story = {
  ...TabletDrawerOpen,
  args: { ...TabletDrawerOpen.args, drawerInitiallyOpen: false },
};

export const MobileDrawerOpen: Story = {
  args: {
    user: { username: "veronica", role: "operador" },
    currentView: "dashboard",
    drawerInitiallyOpen: true,
    children: <DashboardOverview />,
    onLogout,
  },
  parameters: { viewport: { width: 390, height: 844 } },
};

export const Narrow640: Story = {
  ...TabletRail,
  parameters: { viewport: { width: 640, height: 900 } },
};

export const MobileHeaderAndTabs: Story = {
  ...MobileDrawerOpen,
  args: { ...MobileDrawerOpen.args, drawerInitiallyOpen: false },
};

export const Rail1024: Story = {
  ...DesktopAdmin,
  parameters: { viewport: { width: 1024, height: 900 } },
};

export const HeaderZero: Story = {
  ...DesktopAdmin,
  args: { ...DesktopAdmin.args, notificationState: { status: "ready", unread: 0 } },
};

export const HeaderUnread: Story = {
  ...DesktopAdmin,
  args: { ...DesktopAdmin.args, notificationState: { status: "ready", unread: 3 } },
};

export const HeaderError: Story = {
  ...DesktopAdmin,
  args: { ...DesktopAdmin.args, notificationState: { status: "error" } },
};

export const ConversationsSegment: Story = {
  ...DesktopAdmin,
  args: {
    ...DesktopAdmin.args,
    currentView: "conversations",
  },
};

export const CasesSegment: Story = {
  ...DesktopAdmin,
  args: {
    ...DesktopAdmin.args,
    currentView: "conversations",
  },
};
