# Principle Coverage Matrix

This file proves that all 36 design principles are represented in the compact skill bundle.

| # | Principle topic | Primary location |
|---|---|---|
| 1 | Business emits facts; Notification reacts | `notification-core/references/architecture-events.md` |
| 2 | Events describe what happened | `notification-core/references/architecture-events.md` |
| 3 | Producer unaware of listeners | `notification-core/references/architecture-events.md` |
| 4 | Notification not business success dependency | `notification-reliability/references/failure-modes.md` |
| 5 | Atomic state + event / Outbox | `notification-reliability/references/failure-modes.md` |
| 6 | Redelivery + idempotency | `notification-reliability/references/failure-modes.md` |
| 7 | Make duplicates harmless | `notification-reliability/references/failure-modes.md` |
| 8 | Notification has independent Deliveries | `notification-core/references/policy-delivery-inbox.md` |
| 9 | Retry failed unit | `notification-reliability/references/failure-modes.md` |
| 10 | Channel failure isolation | `notification-reliability/references/failure-modes.md` |
| 11 | Split queue/worker when justified | `notification-reliability/references/infrastructure-decision.md` |
| 12 | Transient retry; permanent terminal/DLQ | `notification-reliability/references/failure-modes.md` |
| 13 | Backoff + jitter | `notification-reliability/references/failure-modes.md` |
| 14 | Templates owned by Notification | `notification-core/references/policy-delivery-inbox.md` |
| 15 | Event facts, no presentation | `notification-core/references/architecture-events.md` |
| 16 | Policy vs Preference | `notification-core/references/policy-delivery-inbox.md` |
| 17 | Mandatory override explicit | `notification-core/references/policy-delivery-inbox.md` |
| 18 | Push vs durable Inbox | `notification-core/references/policy-delivery-inbox.md` |
| 19 | Notification is projection | `notification-core/references/policy-delivery-inbox.md` |
| 20 | Open -> current domain state | `notification-core/references/policy-delivery-inbox.md` |
| 21 | No cross-service DB reads | `notification-core/SKILL.md` |
| 22 | Event contract version/backcompat | `notification-core/references/architecture-events.md` |
| 23 | Domain vs Integration Event | `notification-core/references/architecture-events.md` |
| 24 | Sufficient payload, no dump | `notification-core/references/architecture-events.md` |
| 25 | Event identity | `notification-core/references/architecture-events.md` |
| 26 | Correlation ID | `notification-core/references/architecture-events.md` |
| 27 | At-least-once + idempotency | `notification-reliability/SKILL.md` |
| 28 | Eventual consistency intentional | `notification-core/references/architecture-events.md` |
| 29 | Independent channel scaling | `notification-reliability/references/failure-modes.md` |
| 30 | Notification owns communication policy | `notification-core/references/policy-delivery-inbox.md` |
| 31 | Boundaries follow ownership | `notification-core/references/architecture-events.md` |
| 32 | Recovery at failure boundary | `notification-reliability/references/failure-modes.md` |
| 33 | No abstraction before failure mode | `notification-reliability/references/infrastructure-decision.md` |
| 34 | Start simple; split only when needed | `notification-reliability/references/infrastructure-decision.md` |
| 35 | Channel changes don't change producer | `notification-core/references/architecture-events.md` |
| 36 | New consumer doesn't change producer | `notification-core/references/architecture-events.md` |
