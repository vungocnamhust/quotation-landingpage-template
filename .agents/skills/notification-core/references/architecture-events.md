# Architecture and Event Semantics

## Ownership

The source business service owns:
- its aggregate state;
- domain invariants;
- the fact that a business transition occurred.

Notification owns:
- communication policy;
- recipient resolution;
- optional/mandatory channel selection;
- preferences;
- templates;
- notification and delivery state.

A producer must not know whether the reaction is Email, Push, SMS, In-App, analytics, or some future consumer.

## Event vs Command

Good integration events:
- `QuotePublished`
- `QuoteRequestCreated`

Bad event names:
- `CreateQuotePublication`
- `NotifyCustomer`

The first group describes history. The second group instructs a specific reaction and couples the producer to the consumer.

## Domain Event vs Integration Event

Domain Event:
- internal to a bounded context;
- may use richer internal semantics;
- can evolve with the domain model.

Integration Event:
- crosses a service boundary;
- is a stable contract;
- should be versionable and backward compatible;
- should not expose ORM entities or internal implementation structures.

A common flow:

`Aggregate -> Domain Event -> Application mapping -> Integration Event -> transport`

## Event payload

A typical integration-event envelope may contain:
- `eventId`
- `eventType`
- `eventVersion`
- `occurredAt`
- `aggregateId`
- `correlationId`
- `causationId` when useful
- `data`

Include enough stable business data for consumers to react without turning the event into a database dump.

Never put:
- HTML;
- rendered Email/Push copy;
- provider-specific fields;
- unnecessary PII;
- secrets;
- entire ORM/domain graphs.

## Eventual consistency

Notification normally happens after the business transaction commits.

That means:
- the business state may become visible before the notification;
- short delivery delay is acceptable unless the business explicitly requires otherwise.

Do not convert an asynchronous communication concern into a synchronous business dependency just to obtain immediate consistency.
