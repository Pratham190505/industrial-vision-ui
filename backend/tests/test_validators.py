from pathlib import Path
import pytest
from app.core.exceptions import FileValidationError
from app.utils.file_handler import generate_secure_filename, resolve_safe_path
from app.utils.validators import validate_file_size


def test_generate_secure_filename():
    name = generate_secure_filename("test_warehouse_cam1.JPG")
    assert name.endswith(".jpg")
    assert len(name) > 10
    # Different calls produce different names
    assert generate_secure_filename("image.png") != generate_secure_filename("image.png")


def test_resolve_safe_path():
    base = Path("storage/uploads").resolve()
    # Normal filename
    safe_path = resolve_safe_path(base, "image.jpg")
    assert safe_path.parent == base

    # Path traversal attempts
    with pytest.raises(FileValidationError):
        resolve_safe_path(base, "../../../etc/passwd")

    with pytest.raises(FileValidationError):
        resolve_safe_path(base, "..\\..\\windows\\system32")


def test_validate_file_size():
    # 5MB image is valid (limit 10MB)
    validate_file_size(5 * 1024 * 1024, is_video=False)

    # 15MB image exceeds limit
    with pytest.raises(FileValidationError):
        validate_file_size(15 * 1024 * 1024, is_video=False)

    # 100MB video is valid (limit 200MB)
    validate_file_size(100 * 1024 * 1024, is_video=True)

    # 250MB video exceeds limit
    with pytest.raises(FileValidationError):
        validate_file_size(250 * 1024 * 1024, is_video=True)
