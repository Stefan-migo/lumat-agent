import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen, within } from '@testing-library/react';
import { AppShell } from '../../components/domain/AppShell';
import type { User } from '../../types';

const admin: User = { username: 'ana', role: 'admin' };
const operador: User = { username: 'vero', role: 'operador' };

const tokensRaw = readFileSync(
  join(process.cwd(), 'src', 'tokens', 'tokens.css'),
  'utf8',
);
const panelShellRaw = readFileSync(
  join(process.cwd(), 'src', 'components', 'domain', 'PanelShell.tsx'),
  'utf8',
);

/** DS-V1-SHELL — V1 shell. The sidebar brand lives inside `PanelShell`
 *  (sidebar + drawer + mobile bar) with its lime left rule on the V1 green
 *  brand block. The panel header inside the content area is text-only —
 *  dark title, semibold `--text-lg`, on a white `var(--surface)` bar
 *  (same color as the cards) with a hairline `--border` rule, no green
 *  fill, no lime rule — so the page reads as content, not chrome (per the
 *  friendly dashboard reference; this is the post-pivot DS-V1-SHELL shape). */
describe('AppShell stories — v1 sidebar brand + text-only panel header (DS-V1-SHELL)', () => {
  it('renders the sidebar brand block with "Lumat" + "Panel operativo" and no tag', () => {
    render(<AppShell user={admin} />);
    // Brand appears in the desktop sidebar AND in the off-screen drawer;
    // assert at least one and verify the first one carries the lockup.
    const brands = screen.getAllByLabelText(/lumat, panel operativo/i);
    expect(brands.length).toBeGreaterThan(0);
    const brand = brands[0];
    expect(within(brand).getByText('Lumat')).toBeInTheDocument();
    expect(within(brand).getByText(/panel operativo/i)).toBeInTheDocument();
    // The "Design system · v1.0" tag is gone in this iteration.
    expect(within(brand).queryByText(/design system\s+·\s+v1\.0/i)).toBeNull();
  });

  it('uses the --corp-primary contract token for the sidebar brand bg', () => {
    // ponytail: spot-check the raw CSS string so a future "tidy-up" cannot
    // silently swap the brand bg onto a v1 token outside the --corp-* contract.
    expect(panelShellRaw).toMatch(
      /\.panel-shell__brand\s*\{[^}]*background:\s*var\(--corp-primary\)/,
    );
  });

  it('keeps the lime left rule on the sidebar brand', () => {
    expect(panelShellRaw).toMatch(
      /\.panel-shell__brand\s*\{[^}]*border-left:\s*var\(--space-1\)\s+solid\s+var\(--brand-lime\)/,
    );
  });

  it('renders the panel header with the current view label ("Panel" by default)', () => {
    render(<AppShell user={admin} />);
    const header = screen.getByLabelText(/encabezado de la vista/i);
    expect(within(header).getByText('Panel')).toBeInTheDocument();
  });

  it('renders the panel header as text-only — no green fill, no lime rule', () => {
    // ponytail: spot-check the raw CSS string so a future "tidy-up" cannot
    // silently re-add the V1 continuous-bar pattern.
    expect(panelShellRaw).not.toMatch(
      /\.panel-shell__header\s*\{[^}]*background:\s*var\(--primary-800\)/,
    );
    expect(panelShellRaw).not.toMatch(
      /\.panel-shell__header\s*\{[^}]*border-bottom:\s*[^}]*var\(--brand-lime\)/,
    );
  });

  it('uses dark text and semibold text-lg for the panel header title', () => {
    // --corp-fg resolves --text; the header title stays dark after the port.
    expect(panelShellRaw).toMatch(
      /\.panel-shell__header-title\s*\{[^}]*color:\s*var\(--corp-fg\)/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__header-title\s*\{[^}]*font-weight:\s*var\(--weight-semibold\)/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__header-title\s*\{[^}]*font-size:\s*var\(--text-lg\)/,
    );
  });

  it('also renders the brand lockup for the operador shell', () => {
    render(<AppShell user={operador} />);
    expect(screen.getAllByLabelText(/lumat, panel operativo/i).length).toBeGreaterThan(0);
  });

  it('uses cream (#F1F1E8) as the v1 page bg', () => {
    expect(tokensRaw).toMatch(/--bg:\s*#F1F1E8/);
  });

  it('does not reintroduce the dropped --header-gradient token', () => {
    expect(tokensRaw).not.toMatch(/--header-gradient/);
  });
});

describe('AppShell — shell contract port + sidebar bug fixes (DS-SHELL-1..5)', () => {
  it('sizes the collapse toggle 32-36px with a >=40px hit target (DS-SHELL-1)', () => {
    // Bug 1: the shared 44px min-height (calc(space-8 + space-3)) must be
    // escaped by an explicit min-height while the 2.5rem box keeps the hit target.
    expect(panelShellRaw).toMatch(
      /\.panel-shell__collapse-button\s*\{[^}]*min-height:\s*2\.25rem/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__collapse-button\s*\{[^}]*width:\s*2\.5rem/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__collapse-button\s*\{[^}]*height:\s*2\.5rem/,
    );
  });

  it('anchors the toggle in the sidebar rhythm expanded and collapsed (DS-SHELL-1)', () => {
    // Expanded: flush to the nav left/right edges with the shared gap.
    expect(panelShellRaw).toMatch(
      /\.panel-shell__collapse-button\s*\{[^}]*margin:\s*0\s+var\(--space-3\)\s+var\(--space-3\)/,
    );
    // Collapsed: centered under the brand mark.
    expect(panelShellRaw).toMatch(
      /\.panel-shell--collapsed\s+\.panel-shell__collapse-button\s*\{[^}]*align-self:\s*center/,
    );
  });

  it('contains sidebar hover paint via the min-width chain + overflow (DS-SHELL-2)', () => {
    // Bug 2: the flex column min-width:auto shrink-block must be cleared and
    // the sidebar must clip any residual paint past the fixed track.
    expect(panelShellRaw).toMatch(
      /\.panel-shell__sidebar-inner\s*\{[^}]*min-width:\s*0/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__navigation\s*\{[^}]*min-width:\s*0/,
    );
    expect(panelShellRaw).toMatch(
      /\.panel-shell__sidebar\s*\{[^}]*overflow:\s*hidden/,
    );
  });

  it('resolves every PANEL_SHELL_STYLES color/spacing through --corp-*/tokens (DS-SHELL-3)', () => {
    // The whole shell style sheet must be hex-free with no v1 --surface or
    // --primary-8xx leakage (the documented dark-hover exception is --primary-700).
    expect(panelShellRaw).toMatch(/\.panel-shell__sidebar-inner\s*\{[^}]*background:\s*var\(--corp-primary\)/);
    expect(panelShellRaw).toMatch(/\.panel-shell__sidebar\s*\{[^}]*background:\s*var\(--corp-primary\)/);
    expect(panelShellRaw).not.toMatch(/--primary-8\d\d/);
    expect(panelShellRaw).not.toMatch(/--surface/);
    expect(panelShellRaw).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
