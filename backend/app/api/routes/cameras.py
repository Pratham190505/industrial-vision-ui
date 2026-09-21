from fastapi import APIRouter

router = APIRouter(prefix="/cameras", tags=["Live Cameras & Streams"])


@router.get("/")
async def list_cameras():
    """
    List configured warehouse camera streams.
    TODO: Implementation in Live Camera Stream module.
    """
    return {"cameras": []}
