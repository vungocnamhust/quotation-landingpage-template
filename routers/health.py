from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.config import settings
from db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def health_live():
    """Liveness probe: checks if the application is running."""
    return {"status": "ok"}

@router.get("/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe: checks if the application is ready to receive traffic (DB connection works, etc.)."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "ready", "postgres": db_status}
        )

    # Check R2 configuration completeness (not a full ping to avoid slowing down healthcheck)
    if settings.has_r2_configuration:
        r2_status = "ok"
    elif settings.resolved_r2_endpoint or settings.r2_account_id:
        r2_status = "partial_configuration"
    else:
        r2_status = "not_configured"
        
    return {
        "status": "ready",
        "postgres": db_status,
        "r2_config": r2_status
    }
