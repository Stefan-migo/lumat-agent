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
};

export default preview;
