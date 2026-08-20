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
  [/^--brand-/, "Color (brand)"],
  [/^--(?:danger|success|warning)(?:$|-)|^--info$/, "Color (semantic)"],
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

const GROUP_ORDER = [
  "Color",
  "Color (brand)",
  "Color (neutrals)",
  "Color (text)",
  "Color (semantic)",
  "Typography (font/leading/weight)",
  "Typography (scale)",
  "Spacing",
  "Radius",
  "Shadow",
  "Motion",
  "Focus",
  "Breakpoints",
  "z-index",
  "Other",
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
const orderedGroups = [...groups.entries()].sort(
  ([left], [right]) => GROUP_ORDER.indexOf(left) - GROUP_ORDER.indexOf(right),
);

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
    case "Color (brand)":
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
    <main
      style={{
        display: "grid",
        gap: "var(--space-5)",
        maxWidth: "calc(var(--space-8) * 38)",
        margin: "0 auto",
        fontFamily: "var(--font-sans)",
      }}
    >
      <header
        style={{
          display: "grid",
          gap: "var(--space-2)",
          padding: "var(--space-5)",
          borderLeft: "var(--space-1) solid var(--brand-lime)",
          borderRadius: "var(--radius-md)",
          background: "var(--primary-800)",
          color: "var(--surface)",
        }}
      >
        <p style={{ margin: 0, color: "var(--brand-aqua)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)" }}>
          Lumat · Sistema de diseño
        </p>
        <h1 style={{ margin: 0, fontSize: "var(--text-2xl)", lineHeight: "var(--leading-tight)" }}>Design tokens</h1>
        <p style={{ margin: 0, maxWidth: "calc(var(--space-8) * 22)", lineHeight: "var(--leading-normal)" }}>
          Una base operativa sobria: forest estructura, cyan informa y lime reconoce o selecciona.
        </p>
      </header>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, calc(var(--space-8) * 10)), 1fr))",
          gap: "var(--space-4)",
          alignItems: "start",
        }}
      >
      {orderedGroups.map(([group, rows]) => (
        <section
          key={group}
          style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            background: "var(--surface)",
            boxShadow: "var(--shadow-1)",
            overflowX: "auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-2)" }}>
            <h2 style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--text)" }}>{group}</h2>
            <span style={{ color: "var(--text-muted)", fontSize: "var(--text-xs)" }}>{rows.length} tokens</span>
          </div>
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
    </main>
  );
}

const meta = {
  title: "Sistema/Design tokens",
  component: TokensPage,
  excludeStories: ["groupToken"],
  parameters: {
    docs: {
      description: {
        component:
          "Referencia visual del sistema Lumat. Cada valor se lee directamente desde `web/src/tokens/tokens.css` (`?raw`), por lo que Storybook no mantiene una segunda paleta. Forest estructura, cyan informa y lime queda reservado para reconocimiento o selección.",
      },
    },
  },
} satisfies Meta<typeof TokensPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  render: () => <TokensPage />,
};
