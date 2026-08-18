# FastAPI + PostgreSQL Implementation Patterns

## Default stack

Prefer:
- FastAPI;
- Pydantic;
- SQLAlchemy 2.x async or the repository's existing DB layer;
- Alembic if already present;
- PostgreSQL for durable state and invariants;
- lightweight Python worker processes.

Do not introduce a new framework if the repo already has a suitable convention.

## Suggested module shape

Adapt, do not force:

```text
notification/
├── api/
├── domain/
├── application/
├── infrastructure/
│   ├── db/
│   ├── messaging/
│   └── providers/
└── workers/
```

## Database invariants

Prefer DB-enforced correctness:
- unique constraints for dedupe;
- indexes for `(recipient_id, created_at)` and worker status access;
- foreign keys for locally owned data;
- explicit Notification and Delivery tables;
- durable retry timestamps/counters.

Typical dedupe constraint:

`UNIQUE(source_event_id, notification_type, recipient_id)`

Adjust the exact key to business semantics.

## Worker claiming

A PostgreSQL worker may use semantics equivalent to:

```sql
SELECT id
FROM notification_delivery
WHERE status = 'PENDING'
  AND next_attempt_at <= now()
ORDER BY priority DESC, created_at
FOR UPDATE SKIP LOCKED
LIMIT :batch_size;
```

Claim/update rows in a short transaction, commit, then call the provider.

Do not keep a transaction open while waiting on remote I/O.

## Process model

Prefer:
- FastAPI API process;
- one or more worker entrypoints;
- same repository/shared application code.

Do not split into separate microservices until throughput, isolation, or ownership requires it.

## API examples

Potential endpoints:
- `GET /notifications`
- `PATCH /notifications/{id}/read`
- `POST /notifications/read-all`
- `GET /notification-preferences`
- `PUT /notification-preferences`

Always authorize by the authenticated recipient.

## Provider adapters

Provider SDKs stay in infrastructure adapters.

Application/domain code should depend on ports/interfaces, not SendGrid/Twilio/FCM-specific objects.

## Testing

Prioritize:
- transaction rollback;
- outbox creation;
- duplicate event consumption;
- worker concurrency;
- retry scope;
- read/unread authorization;
- provider timeout;
- permanent provider rejection;
- stale notification navigation resolving current domain state.
