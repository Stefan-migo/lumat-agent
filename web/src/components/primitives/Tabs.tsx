import * as RadixTabs from "@radix-ui/react-tabs";
import { useState, type ReactNode } from "react";
import "./primitives.css";

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
 *  click and keyboard activation, uncontrolled by default or controlled via `activeTab`. */
export function Tabs({ tabs, activeTab, onTabChange, children, ariaLabel }: TabsProps) {
  const [internal, setInternal] = useState(tabs[0]?.id ?? "");
  const isControlled = activeTab !== undefined;
  const active = isControlled ? activeTab : internal;

  const handleValueChange = (id: string) => {
    if (!isControlled) setInternal(id);
    onTabChange?.(id);
  };

  return (
    <RadixTabs.Root className="tabs" value={active} onValueChange={handleValueChange}>
      <RadixTabs.List aria-label={ariaLabel}>
        {tabs.map((tab) => (
          <RadixTabs.Trigger key={tab.id} value={tab.id} className="tabs__tab">
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      <RadixTabs.Content value={active} className="tabs__panel">
        {children(active)}
      </RadixTabs.Content>
    </RadixTabs.Root>
  );
}
