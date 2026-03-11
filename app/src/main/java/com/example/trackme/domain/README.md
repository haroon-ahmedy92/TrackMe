# Domain Package

Contains business models, repository interfaces, and use cases.

Guidelines:
- No Android framework APIs here.
- UI and workers should call use cases, not DAOs directly.
- Recovery workflows are explicit and auditable by design.
- Remote actions are guarded by policy-managed capability checks.
