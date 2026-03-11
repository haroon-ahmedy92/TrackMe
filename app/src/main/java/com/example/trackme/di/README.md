# DI Package

Hilt modules that wire the app graph:
- Core primitives (`TimeProvider`, `Hasher`, `Json`).
- Room DAOs and database.
- Retrofit/OkHttp clients.
- Interface bindings for repositories, location provider, and scheduler.

This package should not contain business logic.
