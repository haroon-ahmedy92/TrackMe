import { Badge } from '@/components/ui/Badge';
import type { LocationPrecision } from '@/types/models';

export function LocationPrecisionBadge({ precision }: { precision: LocationPrecision }) {
  const labels: Record<LocationPrecision, string> = {
    precise: 'Precise',
    moderate: 'Moderate',
    approximate: 'Approximate',
  };

  return <Badge variant={precision}>{labels[precision]}</Badge>;
}
