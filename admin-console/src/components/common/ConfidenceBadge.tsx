import { Badge } from '@/components/ui/Badge';
import { formatPercent } from '@/lib/format';

export function ConfidenceBadge({ score }: { score: number }) {
  const variant = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'danger';
  return <Badge variant={variant}>Confidence {formatPercent(score)}</Badge>;
}
