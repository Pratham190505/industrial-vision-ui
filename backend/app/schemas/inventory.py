from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class InventorySnapshotSchema(BaseModel):
    id: Optional[str] = None
    zone: str
    camera_id: Optional[str] = None
    counts: Dict[str, int]
    timestamp: datetime
