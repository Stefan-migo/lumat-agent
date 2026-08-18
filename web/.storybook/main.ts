import type { StorybookConfig } from '@storybook/react-vite';

// Lumat Panel Storybook 8 (B6/T6.3) — React + Vite framework (PDW-CMP-1).
// CSF stories live in src/stories/**/*.stories.tsx mirroring the component
// tree (primitives/ + domain/), documented per PDW-CMP-1.
const config: StorybookConfig = {
  stories: ['../src/stories/**/*.stories.tsx'],
  addons: ['@storybook/addon-essentials'],
  framework: '@storybook/react-vite',
};

export default config;
