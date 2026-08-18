# Infrastructure Decision Guide

The repository is FastAPI + PostgreSQL first.

## Level 0 — synchronous/local

Use only for local operations whose failure should affect the caller.

Do not call external Email/SMS/Push providers from the source business transaction.

## Level 1 — PostgreSQL outbox + workers

Preferred default for moderate workloads.

Use:
- transactional outbox;
- durable Delivery rows;
- worker polling;
- `FOR UPDATE SKIP LOCKED` or equivalent safe claiming;
- `attempt_count`;
- `next_attempt_at`.

Do not hold database locks during provider network calls.

## Level 2 — RabbitMQ

Add only when PostgreSQL workers are insufficient because of a concrete need such as:
- durable fan-out to multiple consumers;
- lower latency push semantics;
- independent queue backpressure;
- strong queue/channel isolation;
- materially different consumer scaling;
- DB polling/claim contention becoming a real bottleneck.

Assume at-least-once delivery and keep consumers idempotent.

## Redis

Use Redis for:
- rate limiting;
- cache;
- short-lived coordination;
- transient optimization.

Do not use Redis as:
- the only durable notification state;
- the only deduplication mechanism;
- evidence of exactly-once delivery.

## New dependency test

For every new infrastructure dependency, answer:
1. Which concrete failure mode does it solve?
2. Why is PostgreSQL insufficient?
3. What operational cost does it add?
4. What happens when it is unavailable?

If these answers are weak, do not add the dependency.
