import type { Meta, StoryObj } from "@storybook/react";
import type { CSSProperties, ReactNode } from "react";
import tokensCss from "../../tokens/tokens.css?raw";

// D8 — ordered first-match group rules. The exact `--text`/`--text-muted` color
// match runs BEFORE the `--text-*` scale rule; unknown tokens fall to "Other"
// (never silently dropped). `base` is included in the scale set: B9 added
// `--text-base: 1rem` (DS-TKN-3) and the design's regex omitted it — leaving a
// known scale token to "Other" would defeat the rule's purpose.
const GROUP_RULES: Array<[RegExp, string]> = [
  [/^--primary-/, "Color"],
  [/^--(?:danger|success|warning)-/, "Color (semantic)"],
  [/^--(?:bg|surface)$|^--border(?:-strong)?$|^--table-head-bg$/, "Color (neutrals)"],
  [/^--text(-muted)?$/, "Color (text)"],
  [/^--text-(xs|base|sm|md|lg|xl|2xl|3xl)$/, "Typography (scale)"],
  [/^--font-|^--leading-|^--weight-/, "Typography (font/leading/weight)"],
  [/^--space-/, "Spacing"],
  [/^--radius-/, "Radius"],
  [/^--shadow-/, "Shadow"],
  [/^--duration-|^--ease-/, "Motion"],
  [/^--focus-ring/, "Focus"],
  [/^--bp-/, "Breakpoints"],
  [/^--z-/, "z-index"],
];

/** D8 first-match group resolution; exported for the drift test (one consumer
 *  besides the page itself). */
export function groupToken(name: string): string {
  for (const [rule, group] of GROUP_RULES) {
    if (rule.test(name)) return group;
  }
  return "Other";
}

// Single source (DS-TOKENS-1): parse tokens.css?raw with the same line regex the
// drift guard uses (D7/D11) — no story-side value duplication.
const tokens = new Map<string, string>();
for (const line of tokensCss.split("\n")) {
  const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
  if (m) tokens.set(m[1], m[2].trim());
}

const groups = new Map<string, Array<[string, string]>>();
for (const [name, value] of tokens) {
  const group = groupToken(name);
  const list = groups.get(group) ?? [];
  list.push([name, value]);
  groups.set(group, list);
}

function sample(group: string, name: string, value: string): ReactNode {
  const box: CSSProperties = {
    width: 48,
    height: 48,
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    display: "inline-block",
    background: "var(--surface)",
  };
  switch (group) {
    case "Color":
    case "Color (semantic)":
    case "Color (neutrals)":
    case "Color (text)":
      return <span style={{ ...box, background: value }} role="img" aria-label={`swatch ${name} = ${value}`} />;
    case "Typography (scale)":
      return <span style={{ fontSize: value, color: "var(--text)" }}>Ag</span>;
    case "Typography (font/leading/weight)":
      return (
        <span
          style={{
            fontFamily: name.startsWith("--font-") ? value : undefined,
            lineHeight: name.startsWith("--leading-") ? value : undefined,
            fontWeight: name.startsWith("--weight-") ? value : undefined,
            color: "var(--text)",
          }}
        >
          Ag
        </span>
      );
    case "Spacing":
      return (
        <span
          style={{
            display: "inline-block",
            width: value,
            height: "var(--space-3)",
            background: "var(--primary-500)",
            borderRadius: "2px",
          }}
        />
      );
    case "Radius":
      return <span style={{ ...box, borderRadius: value }} />;
    case "Shadow":
      return <span style={{ ...box, width: 64, boxShadow: value }} />;
    case "Focus":
      return (
        <span
          style={{
            ...box,
            outline: "var(--focus-ring-width) solid var(--focus-ring)",
            outlineOffset: "var(--focus-ring-offset)",
          }}
        />
      );
    default:
      // Motion / Breakpoints / z-index / Other — plain name+value rows.
      return null;
  }
}

function TokensPage() {
  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      {[...groups.entries()].map(([group, rows]) => (
        <section
          key={group}
          style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--space-3)",
            background: "var(--surface)",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--text)" }}>{group}</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "var(--space-2)" }}>
            <tbody>
              {rows.map(([name, value]) => (
                <tr key={name}>
                  <td style={{ padding: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--text)", fontFamily: "monospace" }}>
                    {name}
                  </td>
                  <td style={{ padding: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>{value}</td>
                  <td style={{ padding: "var(--space-2)", textAlign: "right" }}>{sample(group, name, value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

const meta = {
  title: "Design Tokens",
  component: TokensPage,
  excludeStories: ["groupToken"],
  parameters: {
    docs: {
      description: {
        component:
          "Single-source token reference: every value below is parsed from `web/src/tokens/tokens.css` at build time (`?raw` import, D7) — the page can never drift from the token source (DS-TOKENS-1). Grouping uses the ordered first-match rules (D8): the exact `--text`/`--text-muted` color match precedes the `--text-*` scale rule, and any unknown token surfaces in an **Other** group so nothing is silently dropped.",
      },
    },
  },
} satisfies Meta<typeof TokensPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  render: () => <TokensPage />,
};
