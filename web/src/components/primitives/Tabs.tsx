import { useState, type ReactNode } from "react";

/** Tab definition for the Tabs primitive (catalog `tabs`, corporate). */
export interface TabItem {
  id: string;
  label: ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  /** Controlled mode: the active tab id. Omit for uncontrolled (first tab active). */
  activeTab?: string;
  /** Fired on tab click with the clicked tab id (both modes). */
  onTabChange?: (id: string) => void;
  /** Renders the active panel content. */
  children: (activeId: string) => ReactNode;
  /** Accessible label for the tablist (WAI-ARIA). */
  ariaLabel?: string;
}

/** Corporate Tabs primitive (CORP-TABS-1/2): WAI-ARIA tablist/tab/tabpanel with
 *  click activation, uncontrolled by default or controlled via `activeTab`. */
export function Tabs({ tabs, activeTab, onTabChange, children, ariaLabel }: TabsProps) {
  const [internal, setInternal] = useState(tabs[0]?.id ?? "");
  const active = activeTab ?? internal;

  return (
    <div className="tabs">
      <div role="tablist" aria-label={ariaLabel}>
        {tabs.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              id={`tabs-${tab.id}-tab`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`tabs-${tab.id}-panel`}
              className="tabs__tab"
              onClick={() => {
                if (activeTab === undefined) setInternal(tab.id);
                onTabChange?.(tab.id);
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div id={`tabs-${active}-panel`} role="tabpanel" className="tabs__panel">
        {children(active)}
      </div>
    </div>
  );
}
