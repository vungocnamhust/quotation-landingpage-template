---
name: notification-reliability
description: Reliability rules for outbox, idempotency, PostgreSQL workers, retry/DLQ, RabbitMQ, Redis, queue isolation, and distributed failure handling.
---

# Notification Reliability

Use this skill for asynchronous processing, outbox, idempotency, retry, DLQ, workers, RabbitMQ decisions, Redis usage, and failure isolation.

## Mandatory first step

Read:
- `references/principles.md`
- `references/failure-modes.md`

If infrastructure choice is involved, also read:
- `references/infrastructure-decision.md`

## Required guarantees

Design for:
- no silent lost event when reliability is required;
- at-least-once delivery;
- idempotent local effects;
- independent Delivery state;
- retry at the failed unit;
- failure isolation;
- observable eventual consistency.

Prefer PostgreSQL-backed durable processing before adding a broker.

Never claim end-to-end exactly-once unless every external side effect actually supports the required semantics and the trade-off is documented.
