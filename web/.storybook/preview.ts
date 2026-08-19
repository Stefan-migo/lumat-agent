import { createElement } from 'react';
import type { Preview, Decorator } from '@storybook/react';
import '../src/tokens/tokens.css';

// Global token source (PDW-TKN-1/2): importing tokens.css pins every story to
// the single :root custom-property source. The decorator wraps each story in a
// `.sb-story` div with the shared background + comfortable padding so components
// are reviewed on the real panel surface (--bg), not a bare white canvas.
const withPanelSurface: Decorator = (Story, ctx) =>
  createElement(
    'div',
    { className: 'sb-story', style: { background: 'var(--bg)', padding: 'var(--space-4)' } },
    createElement(Story, ctx),
  );

const preview: Preview = {
  decorators: [withPanelSurface],
  // Global autodocs (DS-STORY-6): SB 8.6 drives autodocs from tags, so the
  // autodocs tag is applied globally here (docs pages without MDX per story).
  tags: ['autodocs'],
  parameters: {
    // Documents intent; SB 8.6 reads the switch from tags, not from parameters.
    docs: { autodocs: true },
    // Viewport presets aligned to the --bp-* reference tokens (DS-STORY-7).
    viewport: {
      viewports: {
        'bp-sm': { name: 'bp-sm (640px)', styles: { width: '640px', height: '900px' }, type: 'mobile' },
        'bp-md': { name: 'bp-md (1024px)', styles: { width: '1024px', height: '900px' }, type: 'tablet' },
        'bp-lg': { name: 'bp-lg (1280px)', styles: { width: '1280px', height: '900px' }, type: 'desktop' },
      },
      defaultViewport: 'bp-lg', // desktop-first panel
    },
  },
};

export default preview;
