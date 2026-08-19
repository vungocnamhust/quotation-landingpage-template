@AGENTS.md
@notification/AGENTS.md

# Quick Commands

## Core Backend (FastAPI - Port 8111)
- Run Dev: `uvicorn main:app --reload --port 8111`
- Run Tests: `PYTHONPATH=. pytest tests/test_domain_rules.py tests/test_business_gates.py tests/test_quote_request_service.py`

## Notification Subsystem (FastAPI - Port 8116)
- Run Service: `uvicorn notification.main:app --reload --port 8116`
- Run Worker: `python -m notification.workers.delivery_worker`
- Run Migrations: `alembic -c notification/alembic.ini upgrade head`
- Run Tests: `PYTHONPATH=. pytest tests/test_notification_api.py`
- Health Check: `curl -s http://localhost:8116/health`

## Docker Compose (Notification Stack)
- Start Notification Stack: `docker compose -f docker-compose.local.yml up -d notification-service notification-worker`
- Check Logs: `docker logs -f quotation-local-notification-service-1`

## Frontend (quote-generator - Port 8115)
- Run Dev: `cd quote-generator && npm run dev`
- Quality Gates: `cd quote-generator && npm run lint && npm run lint:typography && npm run lint:display-system && npm run build`
