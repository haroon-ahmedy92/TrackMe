import type { UserProfile } from '@/types/models';

const TOKEN_KEY = 'trackme_admin_token';
const PROFILE_KEY = 'trackme_admin_profile';

export const authStorage = {
  getToken(): string | null {
    if (typeof window === 'undefined') {
      return null;
    }
    return window.localStorage.getItem(TOKEN_KEY);
  },

  getProfile(): UserProfile | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(PROFILE_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as UserProfile;
    } catch {
      return null;
    }
  },

  setAuth(token: string, profile: UserProfile): void {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  },

  clear(): void {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(PROFILE_KEY);
  },
};
