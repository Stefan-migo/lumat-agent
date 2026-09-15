import { createElement } from 'react';
import type { Preview, Decorator } from '@storybook/react';
import { PanelShell } from '../src/components/domain/PanelShell';
import type { User } from '../src/types';
import '../src/tokens/tokens.css';
import '../src/components/primitives/primitives.css';

const STORYBOOK_USER: User = { username: 'storybook', role: 'admin' };

// Stories whose component already owns the shell (their component IS PanelShell
// or renders it) opt out with `parameters.panelShell = false`; otherwise the
// harness would nest a second shell around them. See PanelEntry and AppShell.
const withPanelShell: Decorator = (Story, ctx) =>
  ctx.parameters.panelShell === false
    ? createElement(Story, ctx)
    : createElement(PanelShell, { user: STORYBOOK_USER }, createElement(Story, ctx));

// Global token source (PDW-TKN-1/2): importing tokens.css pins every story to
// the single :root custom-property source. The decorator wraps each story in a
// `.sb-story` div with the shared background + comfortable padding so components
// are reviewed on the real panel surface (--bg), not a bare white canvas.
const withPanelSurface: Decorator = (Story, ctx) =>
  createElement(
    'div',
    {
      className: 'sb-story',
      style: {
        minHeight: ctx.parameters.layout === 'fullscreen' ? '100vh' : undefined,
        background: 'var(--bg)',
        padding: ctx.parameters.layout === 'fullscreen' ? 0 : 'var(--space-4)',
      },
    },
    createElement(Story, ctx),
  );

const preview: Preview = {
  decorators: [withPanelShell, withPanelSurface],
  // Global autodocs (DS-STORY-6): SB 8.6 drives autodocs from tags, so the
  // autodocs tag is applied globally here (docs pages without MDX per story).
  tags: ['autodocs'],
  parameters: {
    // Documents intent; SB 8.6 reads the switch from tags, not from parameters.
    docs: { autodocs: true },
    // Viewport presets aligned to the --bp-* reference tokens (DS-STORY-7).
    viewport: {
      viewports: {
        'mobile-compact': { name: 'Mobile compact (390px)', styles: { width: '390px', height: '844px' }, type: 'mobile' },
        'bp-sm': { name: 'bp-sm (640px)', styles: { width: '640px', height: '900px' }, type: 'mobile' },
        'tablet-compact': { name: 'Tablet compact (768px)', styles: { width: '768px', height: '1024px' }, type: 'tablet' },
        'bp-md': { name: 'bp-md (1024px)', styles: { width: '1024px', height: '900px' }, type: 'tablet' },
        'bp-lg': { name: 'bp-lg (1280px)', styles: { width: '1280px', height: '900px' }, type: 'desktop' },
      },
      defaultViewport: 'bp-lg', // desktop-first panel
    },
  },
};

export default preview;
