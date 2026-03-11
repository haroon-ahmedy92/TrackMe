# Data Package

Implements domain repositories using local storage, device services, and network clients.

Subareas:
- `local`: Room entities/DAOs/database.
- `preferences`: DataStore-backed scheduling config.
- `repository`: repository implementations and mapping.
- `network`: backend-ready API contracts.

Audit events are append-only and hash-chained for tamper evidence.
Location records include explicit approximate labels and confidence scores.
