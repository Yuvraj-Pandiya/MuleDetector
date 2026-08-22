from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    """Liveness probe — returns 200 when the service is up."""
    return {"status": "ok"}
