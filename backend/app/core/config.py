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
