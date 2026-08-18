---
name: notification-fastapi
description: Implementation guidance for notification APIs, PostgreSQL models, transactions, workers, provider adapters, and tests in a FastAPI/Python repository.
---

# Notification Implementation — FastAPI/PostgreSQL

Use this skill when writing notification code in the repository.

## Mandatory first step

Read:
- `references/implementation-patterns.md`

When architectural or reliability choices are involved, also invoke/read:
- `notification-core`
- `notification-reliability`

## Implementation stance

Default to:
`FastAPI + PostgreSQL + lightweight Python workers`

Keep:
- business facts separate from communication policy;
- provider I/O outside DB transactions;
- Notification and Delivery state explicit;
- DB constraints responsible for correctness where possible;
- provider SDK details behind adapters.

Follow existing repository conventions before introducing a new structure.
