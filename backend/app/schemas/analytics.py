from typing import Dict, List
from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    active_cameras: int
    total_detections_today: int
    active_safety_alerts: int
    inventory_total_items: int
    safety_violations_by_severity: Dict[str, int] = {}
    top_detected_classes: Dict[str, int] = {}
