import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { Icon } from "./Icon";
import "./primitives.css";

export type ToastTone = "success" | "danger" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

export interface ToastApi {
  /** Show a transient notification; it auto-dismisses after the provider's duration. */
  show: (message: string, tone?: ToastTone) => void;
}

const noopToast: ToastApi = { show: () => undefined };
const ToastContext = createContext<ToastApi>(noopToast);

/** App-wide transient notifications, anchored to the bottom-right corner. */
export function ToastProvider({ children, duration = 5000 }: { children: ReactNode; duration?: number }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setItems((previous) => previous.filter((item) => item.id !== id));
  }, []);

  const show = useCallback((message: string, tone: ToastTone = "success") => {
    const id = nextId.current;
    nextId.current += 1;
    setItems((previous) => [...previous, { id, tone, message }]);
    const timer = setTimeout(() => {
      timers.current.delete(timer);
      dismiss(id);
    }, duration);
    timers.current.add(timer);
  }, [dismiss, duration]);

  useEffect(() => () => {
    for (const timer of timers.current) clearTimeout(timer);
    timers.current.clear();
  }, []);

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-region" role="region" aria-label="Notificaciones">
        {items.map((item) => (
          <div key={item.id} className={`toast toast--${item.tone}`} role="status">
            <Icon icon={item.tone === "danger" ? AlertTriangle : item.tone === "info" ? Info : CheckCircle2} size="sm" />
            <p className="toast__message">{item.message}</p>
            <button type="button" className="toast__close" aria-label="Cerrar notificación" onClick={() => dismiss(item.id)}>
              <Icon icon={X} size="sm" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Returns the toast API; a safe no-op when no provider is mounted (e.g. isolated tests). */
export function useToast(): ToastApi {
  return useContext(ToastContext);
}
