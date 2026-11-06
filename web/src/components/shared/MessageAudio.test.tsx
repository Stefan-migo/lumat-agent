import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageAudio } from './MessageAudio';

const SRC = '/panel/api/conversations/9/messages/20/media';

/** jsdom never loads media: duration and currentTime have to be driven by hand. */
function audioEngine(overrides: { duration?: number } = {}) {
  const audio = document.querySelector('audio')!;
  if (overrides.duration !== undefined) {
    Object.defineProperty(audio, 'duration', { value: overrides.duration, configurable: true });
    fireEvent.loadedMetadata(audio);
  }
  return audio;
}

describe('message audio player (panel-polish S3)', () => {
  it('renders designed controls instead of the browser widget', () => {
    render(<MessageAudio src={SRC} />);
    const audio = document.querySelector('audio');
    expect(audio).toHaveAttribute('src', SRC);
    // The native widget is the thing this component replaces: a white pill over the bubble.
    expect(audio).not.toHaveAttribute('controls');
    expect(screen.getByRole('group', { name: /audio/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reproducir audio' })).toBeInTheDocument();
    expect(screen.getByRole('slider', { name: 'Posición del audio' })).toBeInTheDocument();
    // Duration is unknown until the media element reports it; the label says so instead of faking 0:00.
    expect(screen.getByText('0:00 / --:--')).toBeInTheDocument();
  });

  it('prints the real duration once the metadata loads', () => {
    render(<MessageAudio src={SRC} />);
    audioEngine({ duration: 171 });
    expect(screen.getByText('0:00 / 2:51')).toBeInTheDocument();
    expect(screen.getByRole('slider', { name: 'Posición del audio' })).toBeEnabled();
  });

  it('plays and pauses through its own control', async () => {
    const user = userEvent.setup();
    const play = vi.fn().mockResolvedValue(undefined);
    const pause = vi.fn();
    Object.defineProperty(HTMLMediaElement.prototype, 'play', { value: play, configurable: true });
    Object.defineProperty(HTMLMediaElement.prototype, 'pause', { value: pause, configurable: true });
    render(<MessageAudio src={SRC} />);
    const audio = audioEngine({ duration: 60 });

    await user.click(screen.getByRole('button', { name: 'Reproducir audio' }));
    expect(play).toHaveBeenCalledTimes(1);
    fireEvent.play(audio);
    expect(screen.getByRole('button', { name: 'Pausar audio' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Pausar audio' }));
    expect(pause).toHaveBeenCalledTimes(1);
    fireEvent.pause(audio);
    expect(screen.getByRole('button', { name: 'Reproducir audio' })).toBeInTheDocument();
  });

  it('seeks and reports the elapsed position', () => {
    render(<MessageAudio src={SRC} />);
    const audio = audioEngine({ duration: 171 });
    fireEvent.change(screen.getByRole('slider', { name: 'Posición del audio' }), { target: { value: '61' } });
    expect(audio.currentTime).toBe(61);
    expect(screen.getByText('1:01 / 2:51')).toBeInTheDocument();
  });

  it('returns to the start when the audio ends', async () => {
    const user = userEvent.setup();
    Object.defineProperty(HTMLMediaElement.prototype, 'play', { value: vi.fn().mockResolvedValue(undefined), configurable: true });
    render(<MessageAudio src={SRC} />);
    const audio = audioEngine({ duration: 171 });
    await user.click(screen.getByRole('button', { name: 'Reproducir audio' }));
    fireEvent.play(audio);
    fireEvent.change(screen.getByRole('slider', { name: 'Posición del audio' }), { target: { value: '171' } });
    fireEvent.ended(audio);
    expect(screen.getByRole('button', { name: 'Reproducir audio' })).toBeInTheDocument();
    expect(screen.getByText('0:00 / 2:51')).toBeInTheDocument();
  });

  it('reports a media failure with a way to get the file', () => {
    render(<MessageAudio src={SRC} />);
    fireEvent.error(document.querySelector('audio')!);
    expect(screen.getByRole('status')).toHaveTextContent(/no se pudo cargar el audio/i);
    const link = screen.getByRole('link', { name: /descargar audio/i });
    expect(link).toHaveAttribute('href', SRC);
    expect(screen.queryByRole('button', { name: 'Reproducir audio' })).not.toBeInTheDocument();
  });

  it('keeps the operator copy in Spanish and the player tone-neutral', () => {
    render(<MessageAudio src={SRC} label="Audio del cliente" />);
    expect(screen.getByRole('group', { name: 'Audio del cliente' })).toBeInTheDocument();
    expect(screen.queryByText(/play|pause|seek/i)).not.toBeInTheDocument();
  });

  // jsdom cannot evaluate CSS, so the two rules the design depends on are pinned by reading the file:
  // the outbound bubble is dark, and the control has to invert instead of vanishing into it.
  it('inverts its tone inside the dark outbound bubble', () => {
    const css = readFileSync(join(process.cwd(), 'src/components/shared/MessageAudio.css'), 'utf8');
    expect(css).toMatch(/\.ai-agent-grammar__bubble--outbound \.message-audio__toggle \{[^}]*background: var\(--surface\)/);
    expect(css).toMatch(/\.message-audio__toggle:focus-visible/);
  });
});
