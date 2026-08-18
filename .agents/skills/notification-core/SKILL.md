---
name: notification-core
description: Core architectural rules for notification events, orchestration, policy/preferences, inbox semantics, and service boundaries. Use when designing or changing notification behavior.
---

# Notification Core

Use this skill for notification architecture, new notification types, event design, policy/preferences, inbox behavior, and service boundaries.

## Mandatory first step

Read:
- `references/principles.md`

Then read only the references relevant to the task:
- event/boundary work -> `references/architecture-events.md`
- notification/policy/inbox work -> `references/policy-delivery-inbox.md`

## Working rules

Before coding, identify:
1. source bounded context;
2. business fact;
3. Domain Event vs Integration Event boundary;
4. recipient ownership;
5. Notification Policy;
6. Preference handling;
7. Notification vs Delivery state;
8. source of truth for data shown after the user opens the notification.

Reject designs where:
- a business service directly sends Email/SMS/Push;
- an event is a command disguised as history;
- Notification reads another service's private DB;
- a template lives in the producer;
- Push is treated as the durable inbox;
- notification payload is treated as current domain truth.

Keep the architecture as small as possible while preserving the principles.
