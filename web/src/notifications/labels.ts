import { Bell, CalendarDays, CircleAlert, CircleDollarSign, ShieldAlert, type LucideIcon } from 'lucide-react';

export interface NotificationSourcePresentation {
  icon: LucideIcon;
  tone: string;
  label: string;
}

const SOURCE_PRESENTATIONS: Record<string, NotificationSourcePresentation> = {
  appointment: { icon: CalendarDays, tone: 'appointment', label: 'Agenda' },
  emergencia: { icon: ShieldAlert, tone: 'emergency', label: 'Emergencias' },
  cost_alert: { icon: CircleDollarSign, tone: 'cost-alert', label: 'Alertas de costo' },
  notification_failure: { icon: CircleAlert, tone: 'notification-failure', label: 'Fallos de notificación' },
};

export function notificationSourcePresentation(source: string): NotificationSourcePresentation {
  return SOURCE_PRESENTATIONS[source] ?? { icon: Bell, tone: 'default', label: 'Otra notificación' };
}

export function notificationSourceLabel(source: string): string {
  return notificationSourcePresentation(source).label;
}

export function notificationChannelLabel(channel: string | null): string {
  if (!channel) return 'Sin canal';
  const labels: Record<string, string> = { panel: 'Panel', push: 'Notificación push', email: 'Correo electrónico', whatsapp: 'WhatsApp', fallback: 'Canal alternativo' };
  return labels[channel] ?? 'Otro canal';
}
