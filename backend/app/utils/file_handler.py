import os
import uuid
from pathlib import Path
from typing import Tuple
import aiofiles
from fastapi import UploadFile
from app.core.config import get_settings
from app.core.exceptions import FileSizeExceededError, FileValidationError
from app.utils.validators import (
    validate_image_content,
    validate_image_file,
    validate_video_content,
    validate_video_file,
)


def ensure_storage_directories() -> None:
    """Ensure all required local storage directories exist."""
    settings = get_settings()
    directories = [
        settings.upload_path,
        settings.processed_path,
        settings.snapshot_path,
        settings.upload_images_path,
        settings.upload_videos_path,
        settings.processed_images_path,
        settings.processed_videos_path,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def generate_secure_filename(original_filename: str | None) -> str:
    """
    Generate a secure random filename preserving sanitized extension.
    Example: 'warehouse_forklift.jpg' -> 'e4a29a0c...3d.jpg'
    """
    ext = ""
    if original_filename:
        ext = Path(original_filename).suffix.lower()
        # Clean extension of non-alphanumeric chars
        ext = "".join(c for c in ext if c.isalnum() or c == ".")
    if not ext:
        ext = ".jpg"
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{ext}"


def get_annotated_filename(stored_filename: str) -> str:
    """
    Generate annotated filename matching original stored filename pattern.
    Example: 'abc123.jpg' -> 'abc123-annotated.jpg'
    """
    p = Path(stored_filename)
    return f"{p.stem}-annotated{p.suffix}"


def resolve_safe_path(base_directory: Path, filename: str) -> Path:
    """
    Resolve and verify that a target path remains strictly within the intended base directory.
    Prevents path traversal attacks.
    """
    base_dir_resolved = base_directory.resolve()
    target_path = (base_dir_resolved / filename).resolve()

    try:
        target_path.relative_to(base_dir_resolved)
    except ValueError:
        raise FileValidationError(f"Path traversal detected for filename: {filename}")

    return target_path


def get_image_media_type(filename: str) -> str:
    """Return corresponding MIME type for supported image files."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(ext, "image/jpeg")


async def save_upload_image(
    file: UploadFile,
    destination_directory: Path,
    max_bytes: int,
) -> Tuple[str, Path, int, int, int]:
    """
    Validates, streams, and saves an uploaded image.
    Enforces maximum size (raises FileSizeExceededError for 413) and verifies
    using Pillow that the file is not empty, corrupted, or spoofed.

    Returns:
        (stored_filename, safe_destination_path, total_bytes, width, height)
    """
    # 1. Validate extension & MIME type from header first
    validate_image_file(file)

    # 2. Generate secure destination path
    filename = generate_secure_filename(file.filename)
    safe_destination = resolve_safe_path(destination_directory, filename)

    if safe_destination.exists():
        filename = f"{uuid.uuid4().hex}_{filename}"
        safe_destination = resolve_safe_path(destination_directory, filename)

    safe_destination.parent.mkdir(parents=True, exist_ok=True)

    chunks = []
    total_bytes = 0
    chunk_size = 512 * 1024  # 512KB

    try:
        while chunk := await file.read(chunk_size):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise FileSizeExceededError(
                    f"Uploaded image exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB."
                )
            chunks.append(chunk)

        if total_bytes == 0:
            raise FileValidationError("Uploaded image file is empty.")

        all_bytes = b"".join(chunks)

        # 3. Deep validation with Pillow
        width, height, _ = validate_image_content(all_bytes)

        # 4. Write verified bytes to disk
        async with aiofiles.open(safe_destination, "wb") as out_file:
            await out_file.write(all_bytes)

        return filename, safe_destination, total_bytes, width, height

    except Exception:
        # Clean up on failure
        if safe_destination.exists():
            try:
                safe_destination.unlink()
            except OSError:
                pass
        raise


def get_video_media_type(filename: str) -> str:
    """Return corresponding MIME type for supported video files."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }
    return mapping.get(ext, "video/mp4")


async def save_upload_video(
    file: UploadFile,
    destination_directory: Path,
    max_bytes: int,
) -> Tuple[str, Path, int, dict]:
    """
    Validates, streams, and saves an uploaded video file to disk.
    Enforces maximum size on the fly (raises FileSizeExceededError for 413) and
    verifies using OpenCV that the file can be opened and decoded.

    Returns:
        (stored_filename, safe_destination_path, total_bytes, video_metadata)
    """
    # 1. Validate extension & MIME type from header first
    validate_video_file(file)

    # 2. Generate secure destination path
    filename = generate_secure_filename(file.filename)
    safe_destination = resolve_safe_path(destination_directory, filename)

    if safe_destination.exists():
        filename = f"{uuid.uuid4().hex}_{filename}"
        safe_destination = resolve_safe_path(destination_directory, filename)

    safe_destination.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        async with aiofiles.open(safe_destination, "wb") as out_file:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise FileSizeExceededError(
                        f"Uploaded video exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB."
                    )
                await out_file.write(chunk)

        if total_bytes == 0:
            raise FileValidationError("Uploaded video file is empty.")

        # 3. Deep validation with OpenCV
        metadata = validate_video_content(safe_destination)

        return filename, safe_destination, total_bytes, metadata

    except Exception:
        # Clean up partial/corrupted file on failure
        if safe_destination.exists():
            try:
                safe_destination.unlink()
            except OSError:
                pass
        raise
