import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

export function LoadingCard() {
  return (
    <Card>
      <div className="stack">
        <Skeleton width="40%" height={18} />
        <Skeleton width="100%" />
        <Skeleton width="80%" />
      </div>
      <p className="text-muted" style={{ marginTop: 12 }}>
        Low-bandwidth friendly mode: loading lightweight data first.
      </p>
    </Card>
  );
}
