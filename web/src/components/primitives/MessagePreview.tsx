import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import "./primitives.css";

export interface MessagePreviewProps {
  message: ReactNode;
  note?: string;
  name?: string;
  avatarSrc?: string;
}

export function MessagePreview({ message, note, name = "Lumat", avatarSrc }: MessagePreviewProps) {
  return (
    <div className="message-preview">
      <div className="message-preview__row" aria-label={`Mensaje de ${name}`}>
        <Avatar name={name} src={avatarSrc} className="message-preview__avatar" />
        <div className="message-preview__bubble">{message}</div>
      </div>
      {note ? <small className="message-preview__note">{note}</small> : null}
    </div>
  );
}
