# TrackMe Web Admin Console

Web console for lawful, consent-based device recovery and protection workflows.

## Principles
- No covert surveillance features.
- No hidden actions.
- Approximate location methods are labeled clearly and never presented as exact.
- Sensitive actions require confirmation + reason entry for auditability.

## Stack
- Next.js (App Router) + TypeScript
- Reusable design system in plain React components
- Mock API mode for local development (`NEXT_PUBLIC_USE_MOCKS=true`)

## Run
```bash
cd admin-console
npm install
npm run dev
```

## Environment
Copy `.env.example` to `.env.local` and adjust values.

## Project Structure
```text
admin-console/
  src/
    app/
      login/
      (dashboard)/
        devices/
        map/
        incidents/
        geofences/
        audit/
        remote-actions/
        settings/
    components/
      auth/
      layout/
      common/
      ui/
    lib/
      api/
      auth/
      hooks/
      mocks/
    types/
```

## Screen Coverage
- Login shell: `src/app/login/page.tsx`
- Device inventory: `src/app/(dashboard)/devices/page.tsx`
- Device details: `src/app/(dashboard)/devices/[id]/page.tsx`
- Map and last known location: `src/app/(dashboard)/map/page.tsx`
- Incident case page: `src/app/(dashboard)/incidents/page.tsx`
- Geofence management: `src/app/(dashboard)/geofences/page.tsx`
- Audit log viewer: `src/app/(dashboard)/audit/page.tsx`
- Remote action approvals: `src/app/(dashboard)/remote-actions/page.tsx`
- Settings & retention policies: `src/app/(dashboard)/settings/page.tsx`

## Notes
- `src/lib/api/restApi.ts` contains TODO markers where backend endpoint contract may still evolve.
- `src/app/(dashboard)/map/page.tsx` includes a map provider placeholder for Google Maps/Mapbox integration.
