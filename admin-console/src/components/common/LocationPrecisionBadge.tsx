import { Badge } from '@/components/ui/Badge';
import { getCopy } from '@/lib/i18n/copy';
import type { LocationPrecision } from '@/types/models';

export function LocationPrecisionBadge({ precision }: { precision: LocationPrecision }) {
  const ui = getCopy(typeof navigator === 'undefined' ? 'en' : navigator.language);
  const labels: Record<LocationPrecision, string> = {
    precise: ui.labels.precise,
    moderate: ui.labels.moderate,
    approximate: ui.labels.approximate,
  };

  return <Badge variant={precision}>{labels[precision]}</Badge>;
}
