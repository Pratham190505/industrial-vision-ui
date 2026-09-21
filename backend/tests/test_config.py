from app.core.config import Settings, get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.APP_NAME == "WarehouseVision AI"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.MAX_IMAGE_SIZE_MB == 10
    assert settings.MAX_VIDEO_SIZE_MB == 200
    assert settings.max_image_size_bytes == 10 * 1024 * 1024
    assert settings.max_video_size_bytes == 200 * 1024 * 1024


def test_settings_storage_paths():
    settings = get_settings()
    assert settings.upload_path.is_absolute()
    assert settings.processed_path.is_absolute()
    assert settings.snapshot_path.is_absolute()
    assert settings.upload_images_path.name == "images"
    assert settings.upload_videos_path.name == "videos"


def test_safe_repr():
    settings = get_settings()
    repr_str = repr(settings)
    assert "JWT_SECRET_KEY" not in repr_str
    assert settings.JWT_SECRET_KEY not in repr_str
    assert "WarehouseVision AI" in repr_str
