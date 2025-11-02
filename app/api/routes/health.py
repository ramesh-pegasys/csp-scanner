from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Health Check",
                "content": {
                    "application/json": {
                        "example": {"status": "healthy"}
                    }
                }
            }
        }
    },
)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
