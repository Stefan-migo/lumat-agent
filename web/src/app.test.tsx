import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './app';

describe('App shell', () => {
  it('renders the Lumat Panel heading name', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { level: 1, name: /Lumat Panel/i }),
    ).toBeInTheDocument();
  });
});
