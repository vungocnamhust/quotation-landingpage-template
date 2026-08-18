# Notification, Delivery, Policy, Preference, and Inbox

## Notification vs Delivery

A Notification is the semantic communication record.

A Delivery is one attempt/channel path for that Notification.

Example:

```text
Notification N1
├── Delivery EMAIL -> DELIVERED
├── Delivery PUSH  -> FAILED
└── Delivery INAPP -> DELIVERED
```

Successful sibling Deliveries must remain successful when another channel fails.

## Policy vs Preference

Policy answers:
- should this business fact generate communication?
- who should receive it?
- which channels are required?
- which channels are optional?
- what priority/template/locale applies?

Preference answers:
- which optional channels did this recipient enable/disable?

Effective plan:

`system policy + recipient preference + legal/security constraints -> Delivery[]`

Mandatory communication must be explicit, not implemented as a hidden bypass.

## Template ownership

Template rendering belongs to Notification.

The source domain event carries facts and variables; it does not carry final presentation copy.

This allows:
- localization;
- branding changes;
- channel-specific formatting;
- template versioning;
without changing the producer.

## In-App vs Push

Push is ephemeral delivery through OS/provider infrastructure.

In-App Inbox is durable application state.

Server-side inbox state should normally own:
- notification history;
- read/unread;
- archive/delete if supported;
- recipient authorization.

## Projection rule

A notification is historical projection.

If a notification says an Order was shipped and the user opens it later, the client should use a resource action/reference such as:

`OPEN_ORDER { resourceId: "O123" }`

Then fetch current state from the Order service.

Do not render current domain state from stale notification payload.
