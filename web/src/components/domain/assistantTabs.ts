export type WorkspaceTab =
  | { kind: "thread"; threadId: number }
  | { kind: "context"; projectSlug: string }
  | { kind: "history"; projectSlug: string };

const STORAGE_VERSION = 1;
const STORAGE_PREFIX = "lumat:assistant-workspace-tabs";

export function workspaceTabsStorageKey(userId: number): string {
  return `${STORAGE_PREFIX}:user:${userId}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function workspaceTabIdentity(tab: WorkspaceTab): string {
  switch (tab.kind) {
    case "thread": return `thread:${tab.threadId}`;
    case "context":
    case "history": return `${tab.kind}:${tab.projectSlug}`;
  }
}

function parseTab(value: unknown): WorkspaceTab | null {
  if (!isRecord(value)) return null;
  if (value.kind === "thread" && Number.isInteger(value.threadId)) {
    return { kind: "thread", threadId: value.threadId as number };
  }
  if ((value.kind === "context" || value.kind === "history")
    && typeof value.projectSlug === "string" && value.projectSlug.length > 0) {
    return { kind: value.kind, projectSlug: value.projectSlug };
  }
  return null;
}

function uniqueTabs(tabs: readonly WorkspaceTab[]): WorkspaceTab[] {
  const seen = new Set<string>();
  return tabs.filter((tab) => {
    const identity = workspaceTabIdentity(tab);
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

export function readWorkspaceTabState(userId: number): { tabs: WorkspaceTab[]; activeTab: WorkspaceTab | null } {
  try {
    if (!Number.isInteger(userId)) return { tabs: [], activeTab: null };
    const raw = globalThis.localStorage?.getItem(workspaceTabsStorageKey(userId));
    if (!raw) return { tabs: [], activeTab: null };
    const payload: unknown = JSON.parse(raw);
    if (!isRecord(payload) || payload.version !== STORAGE_VERSION || !Array.isArray(payload.tabs)) return { tabs: [], activeTab: null };
    const tabs = uniqueTabs(payload.tabs.map(parseTab).filter((tab): tab is WorkspaceTab => tab !== null));
    const candidate = parseTab(payload.activeTab);
    const activeTab = candidate && tabs.some((tab) => workspaceTabIdentity(tab) === workspaceTabIdentity(candidate)) ? candidate : null;
    return { tabs, activeTab };
  } catch {
    return { tabs: [], activeTab: null };
  }
}

export function readWorkspaceTabs(userId: number): WorkspaceTab[] {
  return readWorkspaceTabState(userId).tabs;
}

export function writeWorkspaceTabs(userId: number, tabs: readonly WorkspaceTab[], activeTab?: WorkspaceTab | null): void {
  try {
    if (!Number.isInteger(userId)) return;
    const safeTabs = tabs.map(parseTab).filter((tab): tab is WorkspaceTab => tab !== null);
    const unique = uniqueTabs(safeTabs);
    const safeActive = activeTab ? parseTab(activeTab) : null;
    const payload = {
      version: STORAGE_VERSION,
      tabs: unique,
      activeTab: safeActive && unique.some((tab) => workspaceTabIdentity(tab) === workspaceTabIdentity(safeActive)) ? safeActive : null,
    };
    globalThis.localStorage?.setItem(workspaceTabsStorageKey(userId), JSON.stringify(payload));
  } catch {
    // Storage is optional; it must never prevent the workspace from rendering.
  }
}

export function mergeWorkspaceTabs(persisted: readonly WorkspaceTab[], routeTabs: readonly WorkspaceTab[]): WorkspaceTab[] {
  return uniqueTabs([...persisted, ...routeTabs]);
}
