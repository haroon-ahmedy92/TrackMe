'use client';

import { Badge } from '@/components/ui/Badge';
import type { DeviceTrustRecord } from '@/types/models';

export function TrustStatusBadge({ trust }: { trust: DeviceTrustRecord | null | undefined }) {
  if (!trust) {
    return <Badge variant="neutral">Trust unavailable</Badge>;
  }

  if (trust.status === 'trusted') {
    return <Badge variant="success">Trusted signals</Badge>;
  }

  if (trust.status === 'caution') {
    return <Badge variant="warning">Needs review</Badge>;
  }

  return <Badge variant="neutral">Signals limited</Badge>;
}
