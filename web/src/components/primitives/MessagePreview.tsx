import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import "./primitives.css";

export interface MessagePreviewProps {
  message: ReactNode;
  note?: string;
  name?: string;
}

export function MessagePreview({ message, note, name = "Lumat" }: MessagePreviewProps) {
  return (
    <div className="message-preview">
      <div className="message-preview__row" aria-label={`Mensaje de ${name}`}>
        <Avatar name={name} className="message-preview__avatar" />
        <div className="message-preview__bubble">{message}</div>
      </div>
      {note ? <small className="message-preview__note">{note}</small> : null}
    </div>
  );
}
