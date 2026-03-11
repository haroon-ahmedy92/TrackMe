# App Routes

This folder defines page routes using Next.js App Router.

- `login/`: unauthenticated login shell.
- `(dashboard)/`: authenticated admin console routes wrapped by `RequireAuth` + `AppShell`.
- `page.tsx`: root redirect to login or dashboard based on local auth token.
