from fastapi import APIRouter

router = APIRouter(prefix="/detections", tags=["Detections"])


@router.get("/")
async def list_detections():
    """
    Retrieve historical detection records.
    TODO: Implementation in Computer Vision Detection module.
    """
    return {"detections": []}
