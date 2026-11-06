import { useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { Icon } from "../primitives/Icon";
import "./MessageAudio.css";

export interface MessageAudioProps {
  src: string;
  /** Accessible name of the player block. The visible "Audio adjunto" label is gone: the controls
   *  and the duration already say what the block is, and it repeated the media type on every row. */
  label?: string;
}

const seconds = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return "0:00";
  const total = Math.floor(value);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

/**
 * Voice-note player for a thread bubble (panel-polish S3).
 *
 * The native `<audio controls>` widget is not usable here: Chromium draws a white pill over the
 * bubble with a fixed 0:00 / 0:00 until the media is fully ready, ignores the panel's tokens, and
 * reads as a browser artifact rather than as a message. This keeps the media element as the engine
 * (hidden) and drives it from three token-styled controls: play/pause, a seek slider and the time
 * pair. The slider is a real `<input type="range">`, so keyboard seeking is free.
 */
export function MessageAudio({ src, label = "Audio adjunto" }: MessageAudioProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <p className="message-audio__error" role="status">
        No se pudo cargar el audio.{" "}
        <a className="message-audio__download" href={src} download>
          Descargar audio
        </a>
      </p>
    );
  }

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) audio.pause();
    else void audio.play().catch(() => setFailed(true));
  };

  const seek = (value: number) => {
    const audio = audioRef.current;
    if (audio) audio.currentTime = value;
    setCurrentTime(value);
  };

  const knownDuration = Number.isFinite(duration) && duration > 0;

  return (
    <div className="message-audio" role="group" aria-label={label}>
      <audio
        ref={audioRef}
        className="message-audio__engine"
        src={src}
        preload="metadata"
        onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          setCurrentTime(0);
        }}
        onError={() => setFailed(true)}
      />
      <button
        type="button"
        className="message-audio__toggle"
        aria-label={playing ? "Pausar audio" : "Reproducir audio"}
        onClick={toggle}
      >
        <Icon icon={playing ? Pause : Play} size="sm" />
      </button>
      <input
        className="message-audio__seek"
        type="range"
        min={0}
        max={knownDuration ? duration : 0}
        step={0.1}
        value={currentTime}
        aria-label="Posición del audio"
        aria-valuetext={`${seconds(currentTime)} de ${knownDuration ? seconds(duration) : "duración desconocida"}`}
        disabled={!knownDuration}
        onChange={(event) => seek(Number(event.currentTarget.value))}
      />
      <span className="message-audio__time">
        {seconds(currentTime)} / {knownDuration ? seconds(duration) : "--:--"}
      </span>
    </div>
  );
}
