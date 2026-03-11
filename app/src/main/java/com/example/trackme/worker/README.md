# Worker Package

Background scheduling and check-in workers.

Components:
- `CheckInScheduler`: schedules normal and lost-mode check-ins.
- `NormalCheckInWorker`: low-frequency baseline updates.
- `LostModeCheckInWorker`: time-boxed elevated update mode.

Workers call domain use cases and produce audit events.
Work constraints are battery-aware and require network connectivity.
