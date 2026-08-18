# Complete Notification Review Checklist

## Domain/event boundary

- Business service emits a fact, not a send command.
- Producer does not know channel/consumer details.
- Notification does not own source-domain business logic.
- Notification does not read another service's private DB.
- Domain Event and Integration Event boundary is explicit where needed.
- Integration Event is versionable/backward compatible.
- Event payload contains facts, not presentation.
- Payload is sufficient but not a domain-object dump.
- Event has stable ID and correlation metadata.

## Business transaction

- Notification/provider success is not required for unrelated business transaction success.
- If event loss matters, business state + outbox intent are atomic.
- Eventual consistency is deliberate and acceptable.

## Idempotency

- Duplicate delivery is assumed possible.
- Consumer is idempotent.
- Dedupe uses durable constraints/state.
- Retry does not recreate already completed effects.
- External provider ambiguity has a mitigation when duplicates matter.

## Notification/Delivery

- Notification and Delivery are separate concepts.
- Each channel has independent state.
- Failed channel does not reset successful channels.
- Retry operates at Delivery level.

## Retry/failure

- Transient vs permanent failures are classified.
- Retry uses bounded backoff and jitter.
- Permanent/poison work reaches terminal state or DLQ.
- Recovery mechanism sits at the boundary where the failure occurs.

## Channel isolation

- Queue/worker separation exists only when backlog, throughput, SLA, or failure isolation requires it.
- Channels can scale independently when needed.
- Bulk traffic cannot starve critical traffic if the product requires an SLA.

## Policy/preferences

- Communication Policy belongs to Notification.
- Preferences filter optional channels.
- Mandatory communication is explicit and can override optional preference.
- Templates belong to Notification.

## Inbox/source of truth

- Push is not used as durable inbox state.
- In-App Inbox is durable when product history/read state requires it.
- Notification is treated as projection.
- Opening a notification resolves current state from the owning domain service.

## Infrastructure

- PostgreSQL is preferred before adding queue infrastructure.
- RabbitMQ is justified by a named failure/scale mode.
- Redis is not the primary durable source of truth.
- No abstraction exists solely because it is fashionable.

## Simplicity

- Start simple.
- Split process/service only because throughput, isolation, or ownership requires it.
- Adding a channel does not require editing the business producer.
- Adding a consumer does not require editing the producer.

## Observability

Traceability can answer:
- which event caused this notification;
- which business flow caused the event;
- whether the event was consumed;
- what Notification was created;
- which channels were selected;
- which Delivery failed;
- retry count;
- provider result;
- queue/outbox lag.

Avoid secrets and unnecessary PII in logs.
