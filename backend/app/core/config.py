from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory: .../backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "WarehouseVision AI"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "warehousevision"

    # Security & Authentication
    JWT_SECRET_KEY: str = "replace_with_a_secure_secret_min_32_characters_for_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Frontend CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Storage Paths (relative to backend dir or absolute)
    UPLOAD_DIR: str = "storage/uploads"
    PROCESSED_DIR: str = "storage/processed"
    SNAPSHOT_DIR: str = "storage/snapshots"

    # Computer Vision & File Size Limits
    YOLO_MODEL_PATH: str = "yolo11n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.40
    YOLO_IOU_THRESHOLD: float = 0.45
    YOLO_DEVICE: str = "cpu"
    YOLO_IMAGE_SIZE: int = 640
    YOLO_MAX_DETECTIONS: int = 100
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_VIDEO_SIZE_MB: int = 200
    VIDEO_FRAME_INTERVAL: int = 1

    # Object Tracking (ByteTrack / BoT-SORT)
    TRACKER_TYPE: str = "bytetrack"
    TRACKER_CONFIDENCE_THRESHOLD: float = 0.25
    TRACKER_IOU_THRESHOLD: float = 0.5
    TRACKER_MAX_AGE: int = 30  # informational; ByteTrack uses its YAML config internally

    # Safety Monitoring
    SAFETY_ENABLED: bool = True
    PERSON_CLASSES: str = "person"
    FORKLIFT_CLASSES: str = "forklift"
    PROXIMITY_WARNING_DISTANCE: float = 100.0
    COLLISION_WARNING_DISTANCE: float = 50.0
    RESTRICTED_ZONE_ENABLED: bool = True
    EVENT_COOLDOWN_SECONDS: float = 5.0
    VELOCITY_WINDOW_FRAMES: int = 5

    # PPE Compliance Monitoring
    PPE_ENABLED: bool = True
    PPE_MODEL_PATH: str = ""  # empty = use main model if it has PPE classes
    PPE_HELMET_CLASSES: str = "helmet,safety helmet"
    PPE_VEST_CLASSES: str = "vest,safety vest"
    PPE_GLOVE_CLASSES: str = "gloves,glove"
    PPE_SHOE_CLASSES: str = "boots,safety shoes"
    REQUIRED_PPE: str = "helmet,vest"
    PPE_ASSOCIATION_IOU_THRESHOLD: float = 0.10
    PPE_MISSING_CONFIRMATION_FRAMES: int = 5
    PPE_EVENT_COOLDOWN_SECONDS: float = 10.0

    # Inventory Monitoring
    INVENTORY_ENABLED: bool = True
    INVENTORY_CLASSES: str = "box,pallet,crate"
    INVENTORY_CONFIDENCE_THRESHOLD: float = 0.40
    INVENTORY_COUNT_MODE: str = "visible"
    INVENTORY_SNAPSHOT_INTERVAL_SECONDS: float = 10.0
    INVENTORY_CHANGE_THRESHOLD: int = 1
    INVENTORY_LOW_STOCK_ENABLED: bool = True
    INVENTORY_EVENT_COOLDOWN_SECONDS: float = 10.0
    INVENTORY_THRESHOLDS_JSON: str = '{"box": 5, "pallet": 2, "crate": 3}'

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and ("replace_with" in v or len(v) < 32):
            raise ValueError("JWT_SECRET_KEY must be a secure, high-entropy key of at least 32 characters in production.")
        return v

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def processed_path(self) -> Path:
        path = Path(self.PROCESSED_DIR)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def snapshot_path(self) -> Path:
        path = Path(self.SNAPSHOT_DIR)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def upload_images_path(self) -> Path:
        return self.upload_path / "images"

    @property
    def upload_videos_path(self) -> Path:
        return self.upload_path / "videos"

    @property
    def processed_images_path(self) -> Path:
        return self.processed_path / "images"

    @property
    def processed_videos_path(self) -> Path:
        return self.processed_path / "videos"

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    @property
    def max_video_size_bytes(self) -> int:
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024

    @property
    def person_classes_set(self) -> set:
        return {c.strip().lower() for c in self.PERSON_CLASSES.split(",") if c.strip()}

    @property
    def forklift_classes_set(self) -> set:
        return {c.strip().lower() for c in self.FORKLIFT_CLASSES.split(",") if c.strip()}

    @property
    def ppe_helmet_classes_set(self) -> set:
        return {c.strip().lower() for c in self.PPE_HELMET_CLASSES.split(",") if c.strip()}

    @property
    def ppe_vest_classes_set(self) -> set:
        return {c.strip().lower() for c in self.PPE_VEST_CLASSES.split(",") if c.strip()}

    @property
    def ppe_glove_classes_set(self) -> set:
        return {c.strip().lower() for c in self.PPE_GLOVE_CLASSES.split(",") if c.strip()}

    @property
    def ppe_shoe_classes_set(self) -> set:
        return {c.strip().lower() for c in self.PPE_SHOE_CLASSES.split(",") if c.strip()}

    @property
    def required_ppe_set(self) -> set:
        return {c.strip().lower() for c in self.REQUIRED_PPE.split(",") if c.strip()}

    @property
    def inventory_classes_set(self) -> set:
        return {c.strip().lower() for c in self.INVENTORY_CLASSES.split(",") if c.strip()}

    @property
    def inventory_thresholds(self) -> dict:
        import json
        try:
            parsed = json.loads(self.INVENTORY_THRESHOLDS_JSON)
            if isinstance(parsed, dict):
                return {str(k).strip().lower(): int(v) for k, v in parsed.items()}
        except Exception:
            pass
        return {"box": 5, "pallet": 2, "crate": 3}

    def __repr__(self) -> str:
        # Safe repr avoiding printing secrets
        return (
            f"<Settings app_name='{self.APP_NAME}' env='{self.ENVIRONMENT}' "
            f"debug={self.DEBUG} db='{self.MONGODB_DATABASE}'>"
        )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
