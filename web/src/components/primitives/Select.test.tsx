import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Select } from './Select';

const options = [
  { value: 'nuevo', label: 'Nuevo' },
  { value: 'activo', label: 'Activo' },
];

// T7.3 — Select (PDW-CMP-1). Options from props, label association,
// controlled value rendering, onChange on selection, error/aria, disabled.
describe('Select (T7.3)', () => {
  it('associates the label and renders the options with their values', () => {
    render(<Select label="Estado" options={options} defaultValue="nuevo" />);
    const select = screen.getByLabelText('Estado');
    expect(select.tagName).toBe('SELECT');
    expect(select).toHaveAttribute('data-bx-size', 'md');
    for (const o of options) {
      const option = screen.getByRole('option', { name: o.label }) as HTMLOptionElement;
      expect(option.value).toBe(o.value);
    }
  });

  it('shows the controlled value as the selected option', () => {
    render(<Select label="Estado" options={options} value="activo" onChange={() => {}} />);
    const select = screen.getByLabelText('Estado') as HTMLSelectElement;
    expect(select.value).toBe('activo');
  });

  it('renders the sm size via the data-bx-size contract', () => {
    render(<Select label="Estado" options={options} defaultValue="" size="sm" />);
    expect(screen.getByLabelText('Estado')).toHaveAttribute('data-bx-size', 'sm');
  });

  it('fires onChange when a different option is chosen', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Select label="Estado" options={options} value="nuevo" onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText('Estado'), 'activo');
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('renders the error and marks aria-invalid + links aria-describedby', () => {
    render(
      <Select label="Estado" options={options} defaultValue="" error="Seleccione un estado" />,
    );
    const select = screen.getByLabelText('Estado');
    expect(select).toHaveAttribute('aria-invalid', 'true');
    const describedBy = select.getAttribute('aria-describedby');
    expect(describedBy).toBeTruthy();
    const message = screen.getByText('Seleccione un estado');
    expect(message).toBeInTheDocument();
    expect(message.id).toBe(describedBy);
  });

  it('disables the select when disabled is set', () => {
    render(<Select label="Estado" options={options} defaultValue="" disabled />);
    expect(screen.getByLabelText('Estado')).toBeDisabled();
  });
});
