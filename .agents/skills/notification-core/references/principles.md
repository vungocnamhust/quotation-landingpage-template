# Notification Design Principles

These are the non-negotiable design principles for the notification subsystem.

1. **Business service only emits facts; Notification Service decides how to react.**
2. **An event says what happened, not what should be sent.**
3. **A producer does not need to know who is listening to its event.**
4. **Notification must not become a condition for the originating business transaction to succeed.**
5. **Business state and the event intent must be recorded atomically when reliability requires it; use the Outbox pattern.**
6. **Assume events may be redelivered; consumers must be idempotent.**
7. **Do not try to eliminate duplicates at all costs; make duplicates harmless.**
8. **One Notification may have many Deliveries; each Delivery has independent state.**
9. **Retry where the failure occurs; do not retry the whole workflow.**
10. **One failed channel must not pull other channels down with it.**
11. **Split queues/workers when backlog, throughput, or failure isolation requires it.**
12. **Retry transient failures; send permanent/poison failures to a terminal state or DLQ.**
13. **Retry with bounded backoff and jitter; do not DDoS your own system or provider.**
14. **Templates belong to Notification, not to the source domain service.**
15. **Events contain business data, not HTML or final presentation text.**
16. **Policy decides what should be communicated; Preference decides which optional communication the user allows.**
17. **Mandatory notifications must be able to override optional user preferences explicitly.**
18. **Push is a delivery channel; the In-App Inbox is the durable notification state.**
19. **Notification is a projection of an event, not the source of truth of the originating domain.**
20. **When a user opens a notification, retrieve current state from the owning domain service.**
21. **Do not read another service's private database to construct notifications.**
22. **An event contract is an API between services; version it and preserve backward compatibility.**
23. **Domain Events are internal to a bounded context; Integration Events cross service boundaries.**
24. **Events contain enough data for consumers to work, but do not dump the whole domain object.**
25. **Every event has stable identity for deduplication and tracing.**
26. **Correlation ID should answer which business flow caused a notification.**
27. **Prefer at-least-once delivery + idempotency over fragile exactly-once assumptions.**
28. **Eventual consistency is an intentional trade-off, not a bug.**
29. **Scale each channel according to its own demand; do not force all channels to scale together.**
30. **Notification Service owns communication policy, not the originating domain's internal business logic.**
31. **Service boundaries follow ownership of data and decisions.**
32. **Put recovery mechanisms where failures occur.**
33. **Do not add abstractions before a real failure mode requires them.**
34. **Start simple; split workers/services only when throughput, isolation, or ownership requires it.**
35. **Changing/adding a delivery channel should not require changing a business service.**
36. **Adding a new consumer should not require changing the producer.**

## Eight-line compass

> **Emit facts, not commands.**  
> **Producer owns the event; consumer owns the reaction.**  
> **Business success must not depend on notification success.**  
> **Never lose an event; tolerate duplicates.**  
> **Retry the failed delivery, not the whole notification.**  
> **Isolate channels and failures.**  
> **Notification is a projection, never the source of truth.**  
> **Prefer explicit boundaries over hidden coupling.**
