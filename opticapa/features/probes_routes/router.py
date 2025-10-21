from fastapi import APIRouter, status


probe_router = APIRouter(prefix="", tags=["probe"])


@probe_router.get("/health", status_code=status.HTTP_200_OK)
@probe_router.get("/health/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Utility function to check health of the application
    Args:

    Returns:

    """
    return {"status": "ok"}


@probe_router.get("/ready", status_code=status.HTTP_200_OK)
@probe_router.get("/ready/", status_code=status.HTTP_200_OK)
async def ready_check():
    """
    Utility function to check if the application is ready
    Args:

    Returns:

    """
    return {"status": "ok"}
