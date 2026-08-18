import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

// T7.1 — Button (PDW-CMP-1). Behavioral tests: tag selection (button vs anchor),
// click handling, disabled guard, and className passthrough contract.
describe('Button (T7.1)', () => {
  it('renders a <button> by default with the given children as its accessible name', () => {
    render(<Button>Guardar</Button>);
    const btn = screen.getByRole('button', { name: 'Guardar' });
    expect(btn.tagName).toBe('BUTTON');
    expect(btn).toBeEnabled();
  });

  it('renders an anchor when href is provided, with the same children and href', () => {
    render(<Button href="/panel/export/clients.csv">Exportar</Button>);
    const link = screen.getByRole('link', { name: 'Exportar' });
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', '/panel/export/clients.csv');
  });

  it('fires onClick on click, but not when disabled', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    const { unmount } = render(<Button onClick={onClick}>Aceptar</Button>);
    await user.click(screen.getByRole('button', { name: 'Aceptar' }));
    expect(onClick).toHaveBeenCalledTimes(1);
    unmount();

    render(
      <Button onClick={onClick} disabled>
        Bloqueado
      </Button>,
    );
    await user.click(screen.getByRole('button', { name: 'Bloqueado' }));
    expect(onClick).toHaveBeenCalledTimes(1); // unchanged — disabled never fires
    expect(screen.getByRole('button', { name: 'Bloqueado' })).toBeDisabled();
  });

  it('passes a custom className through to the rendered element', () => {
    const { container } = render(<Button className="my-custom-button">Algo</Button>);
    const custom = container.querySelector('.my-custom-button');
    expect(custom).not.toBeNull();
    expect(custom).toHaveTextContent('Algo');
  });

  it('renders both variants as enabled buttons (visual difference is token-only, PDW-TKN-2)', () => {
    render(<Button variant="primary">Guardar</Button>);
    render(<Button variant="secondary">Cancelar</Button>);
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeEnabled();
  });
});
