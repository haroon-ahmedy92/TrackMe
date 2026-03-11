export const formatDateTime = (value: string): string =>
  new Date(value).toLocaleString('en-TZ', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

export const formatRelativeStatus = (online: boolean): string => (online ? 'Online' : 'Offline');

export const formatPercent = (value: number): string => `${Math.max(0, Math.min(100, value))}%`;
