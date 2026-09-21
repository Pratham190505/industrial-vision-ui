from fastapi import APIRouter

router = APIRouter(prefix="/safety", tags=["Safety Monitoring"])


@router.get("/zones")
async def list_safety_zones():
    """
    List configured safety exclusion and hazard zones.
    TODO: Implementation in Safety Zone module.
    """
    return {"zones": []}


@router.get("/events")
async def list_safety_events():
    """
    List safety violation events.
    TODO: Implementation in Safety Zone module.
    """
    return {"events": []}
