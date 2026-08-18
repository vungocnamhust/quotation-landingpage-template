---
name: notification-review
description: Review gate for notification architecture, reliability, event boundaries, retry, infrastructure, observability, and compliance with the subsystem design principles.
---

# Notification Review Gate

Use this skill before merging or when auditing notification changes.

## Mandatory first step

Read:
- `references/review-checklist.md`
- `references/principle-coverage.md`

For deep architectural/reliability questions, read the relevant references from:
- `notification-core`
- `notification-reliability`

## Review output

Classify findings:
- BLOCKER — correctness, data loss, duplicate critical side effect, security, or boundary violation.
- HIGH — likely outage, severe coupling, or operational failure.
- MEDIUM — maintainability, scale, or future reliability issue.
- LOW — optional improvement.

For every finding include:
1. exact file/location;
2. violated principle;
3. concrete failure scenario;
4. smallest viable fix.

Do not recommend RabbitMQ, Redis, extra workers, or a new abstraction without naming the failure mode it solves.
