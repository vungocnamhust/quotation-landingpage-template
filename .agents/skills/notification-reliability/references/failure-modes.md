# Reliability Failure Modes

## Lost event / dual-write

Risk:

`commit business state -> process crash -> publish never happens`

Mitigation:
- write business state and outbox record in one local DB transaction;
- publish asynchronously afterward.

## Duplicate event

Risk:
- publisher crashes after publish but before marking success;
- broker redelivers;
- consumer restarts before acknowledgement.

Mitigation:
- stable `eventId`;
- idempotent consumer;
- PostgreSQL unique constraints;
- provider idempotency keys when available.

Do not rely on exactly-once assumptions.

## Partial channel failure

Risk:

```text
EMAIL success
PUSH success
SMS failure
```

Mitigation:
- one independent Delivery per channel;
- retry the SMS Delivery only.

## Provider outage / retry storm

Mitigation:
- transient/permanent failure classification;
- bounded exponential backoff;
- jitter;
- respect `Retry-After`;
- terminal status / DLQ for non-recoverable work.

## Noisy neighbor / backlog

Risk:
- bulk Email traffic delays critical Push/SMS.

Mitigation:
- split workers/queues only when SLA, throughput, or failure isolation justifies it;
- scale channels independently.

## Operational blindness

Preserve:
- eventId;
- correlationId;
- notificationId;
- deliveryId;
- providerMessageId where useful.

Measure:
- outbox/consumer lag;
- delivery latency;
- retries;
- terminal failures;
- provider throttling;
- DLQ depth.
