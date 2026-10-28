import { afterEach, describe, expect, it } from "vitest";
import {
  mergeWorkspaceTabs,
  readWorkspaceTabState,
  readWorkspaceTabs,
  workspaceTabsStorageKey,
  writeWorkspaceTabs,
  type WorkspaceTab,
} from "./assistantTabs";

afterEach(() => localStorage.clear());

describe("assistant tabs persistence", () => {
  it("round trips tabs in order under a per-user key", () => {
    const tabs: WorkspaceTab[] = [
      { kind: "thread", threadId: 7 },
      { kind: "context", projectSlug: "operaciones" },
    ];

    writeWorkspaceTabs(42, tabs, tabs[1]);

    expect(workspaceTabsStorageKey(42)).not.toBe(workspaceTabsStorageKey(43));
    expect(JSON.parse(localStorage.getItem(workspaceTabsStorageKey(42))!)).toEqual({ version: 1, tabs, activeTab: tabs[1] });
    expect(readWorkspaceTabs(42)).toEqual(tabs);
    expect(readWorkspaceTabState(42)).toEqual({ tabs, activeTab: tabs[1] });
  });

  it("treats corrupt, obsolete and unavailable storage as an empty list", () => {
    localStorage.setItem(workspaceTabsStorageKey(1), "{");
    expect(readWorkspaceTabs(1)).toEqual([]);

    localStorage.setItem(workspaceTabsStorageKey(1), JSON.stringify({ tabs: [{ kind: "thread", threadId: 2 }] }));
    expect(readWorkspaceTabs(1)).toEqual([]);

    const original = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", { configurable: true, get: () => { throw new Error("storage unavailable"); } });
    try {
      expect(readWorkspaceTabs(1)).toEqual([]);
      expect(() => writeWorkspaceTabs(1, [])).not.toThrow();
    } finally {
      if (original) Object.defineProperty(window, "localStorage", original);
    }
  });

  it("filters unknown kinds, invalid thread ids, and duplicate tabs", () => {
    localStorage.setItem(workspaceTabsStorageKey(1), JSON.stringify({ version: 1, tabs: [
      { kind: "thread", threadId: 3 },
      { kind: "thread", threadId: 3 },
      { kind: "thread", threadId: 1.5 },
      { kind: "mystery", slug: "x" },
      { kind: "context", projectSlug: "ops" },
      { kind: "context", projectSlug: "ops" },
    ] }));

    expect(readWorkspaceTabs(1)).toEqual([
      { kind: "thread", threadId: 3 },
      { kind: "context", projectSlug: "ops" },
    ]);
  });

  it("appends and activates the deep link without letting persisted tabs displace it", () => {
    const persisted: WorkspaceTab[] = [
      { kind: "thread", threadId: 1 },
      { kind: "context", projectSlug: "ops" },
    ];
    const route: WorkspaceTab[] = [{ kind: "thread", threadId: 2 }];

    expect(mergeWorkspaceTabs(persisted, route)).toEqual([...persisted, ...route]);
    expect(mergeWorkspaceTabs(persisted, [{ kind: "thread", threadId: 1 }])).toEqual(persisted);
  });

  it("keeps a closed tab gone when the updated list is written", () => {
    writeWorkspaceTabs(1, [{ kind: "thread", threadId: 1 }, { kind: "thread", threadId: 2 }]);
    writeWorkspaceTabs(1, [{ kind: "thread", threadId: 2 }]);

    expect(readWorkspaceTabs(1)).toEqual([{ kind: "thread", threadId: 2 }]);
  });
});

describe("per-user isolation", () => {
  it("never shows one user's tabs to another user on the same browser", () => {
    writeWorkspaceTabs(7, [{ kind: "thread", threadId: 41 }, { kind: "context", projectSlug: "obra-sur" }], { kind: "thread", threadId: 41 });

    expect(readWorkspaceTabState(7).tabs).toHaveLength(2);
    expect(readWorkspaceTabState(8)).toEqual({ tabs: [], activeTab: null });
    expect(readWorkspaceTabs(8)).toEqual([]);
  });

  it("ignores a non-integer user id instead of sharing a fallback key", () => {
    writeWorkspaceTabs(Number.NaN, [{ kind: "thread", threadId: 41 }]);

    expect(readWorkspaceTabs(Number.NaN)).toEqual([]);
    expect(readWorkspaceTabs(0)).toEqual([]);
  });
});
