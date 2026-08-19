@AGENTS.md

# Quick Commands

## Backend (FastAPI)
- Run Dev: `uvicorn main:app --reload --port 8111`
- Run Tests: `python -m pytest tests`

## Frontend (quote-generator)
- Run Dev: `cd quote-generator && npm run dev`
- Quality Gates: `cd quote-generator && npm run lint && npm run lint:typography && npm run lint:display-system && npm run build`
