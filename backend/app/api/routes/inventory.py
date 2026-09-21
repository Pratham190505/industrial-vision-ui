from fastapi import APIRouter

router = APIRouter(prefix="/inventory", tags=["Inventory Counting"])


@router.get("/summary")
async def get_inventory_summary():
    """
    Get current warehouse inventory count summary.
    TODO: Implementation in Inventory Counting module.
    """
    return {"summary": {}, "timestamp": None}
