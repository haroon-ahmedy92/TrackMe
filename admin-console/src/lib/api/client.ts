import { restApiClient } from '@/lib/api/restApi';
import type { ApiClient } from '@/lib/api/types';
import { mockApiClient } from '@/lib/mocks/mockApi';

const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';

export const apiClient: ApiClient = useMocks ? mockApiClient : restApiClient;
