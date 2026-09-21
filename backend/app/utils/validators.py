import io
from pathlib import Path
from typing import Set, Tuple
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from app.core.config import get_settings
from app.core.exceptions import FileSizeExceededError, FileValidationError

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_VIDEO_MIME_TYPES: Set[str] = {
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
}

ALLOWED_PIL_FORMATS: Set[str] = {"JPEG", "PNG", "WEBP"}
MAX_DIMENSION: int = 8192


def validate_image_file(file: UploadFile) -> None:
    """
    Validate that the uploaded file has an allowed image extension and MIME type.
    Raises FileValidationError if invalid.
    """
    if not file.filename:
        raise FileValidationError("Uploaded file has no filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise FileValidationError(f"Invalid image file extension '{ext}'. Allowed extensions: {allowed}")

    if file.content_type and file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        allowed_mimes = ", ".join(sorted(ALLOWED_IMAGE_MIME_TYPES))
        raise FileValidationError(
            f"Invalid image MIME type '{file.content_type}'. Allowed MIME types: {allowed_mimes}"
        )


def validate_video_file(file: UploadFile) -> None:
    """
    Validate that the uploaded file has an allowed video extension and MIME type.
    Raises FileValidationError if invalid.
    """
    if not file.filename:
        raise FileValidationError("Uploaded file has no filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise FileValidationError(f"Invalid video file extension '{ext}'. Allowed extensions: {allowed}")

    if file.content_type and file.content_type not in ALLOWED_VIDEO_MIME_TYPES:
        allowed_mimes = ", ".join(sorted(ALLOWED_VIDEO_MIME_TYPES))
        raise FileValidationError(
            f"Invalid video MIME type '{file.content_type}'. Allowed MIME types: {allowed_mimes}"
        )


def validate_file_size(size_bytes: int, is_video: bool = False) -> None:
    """
    Validate raw byte size against configured limits.
    Raises FileSizeExceededError (HTTP 413) if exceeded.
    """
    settings = get_settings()
    max_bytes = settings.max_video_size_bytes if is_video else settings.max_image_size_bytes
    max_mb = settings.MAX_VIDEO_SIZE_MB if is_video else settings.MAX_IMAGE_SIZE_MB

    if size_bytes > max_bytes:
        media_type = "Video" if is_video else "Image"
        raise FileSizeExceededError(
            f"{media_type} exceeds maximum permitted upload limit of {max_mb} MB ({size_bytes} bytes)."
        )


def validate_image_content(content_bytes: bytes) -> Tuple[int, int, str]:
    """
    Verify image bytes using Pillow:
    1. Checks non-empty bytes.
    2. Validates image can be opened and decoded.
    3. Verifies format is JPEG, PNG, or WEBP.
    4. Guards against decompression bombs/extreme dimensions.
    Returns (width, height, format_name) or raises FileValidationError.
    """
    if not content_bytes or len(content_bytes) == 0:
        raise FileValidationError("Uploaded image file is empty.")

    try:
        with Image.open(io.BytesIO(content_bytes)) as img:
            img_format = (img.format or "").upper()
            if img_format not in ALLOWED_PIL_FORMATS:
                raise FileValidationError(
                    f"Unsupported image format '{img_format}'. Supported formats: JPEG, PNG, WEBP."
                )

            width, height = img.size
            if width <= 0 or height <= 0:
                raise FileValidationError("Invalid image dimensions.")

            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise FileValidationError(
                    f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION}."
                )

            # verify integrity
            img.verify()

        # Re-open briefly to ensure image is readable post-verify
        with Image.open(io.BytesIO(content_bytes)) as img:
            img.load()

        return width, height, img_format

    except UnidentifiedImageError:
        raise FileValidationError("The uploaded file could not be identified as a valid image.")
    except FileValidationError:
        raise
    except Exception as exc:
        raise FileValidationError(f"Invalid or corrupted image data: {str(exc)}")


def validate_video_content(file_path: Path) -> dict:
    """
    Verify video file decodability using OpenCV:
    1. Checks file existence and non-zero size.
    2. Opens with cv2.VideoCapture.
    3. Reads first frame to confirm decodable stream.
    4. Extracts metadata: width, height, fps, total_frames, duration_seconds, codec.
    Returns metadata dict or raises FileValidationError.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise FileValidationError("Uploaded video file is empty or missing.")

    import cv2

    cap = cv2.VideoCapture(str(file_path))
    try:
        if not cap.isOpened():
            raise FileValidationError("Could not open video file. Format or codec may be unsupported or file corrupted.")

        ret, frame = cap.read()
        if not ret or frame is None:
            raise FileValidationError("Could not read frames from video file. File may be corrupted or invalid.")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0:
            height, width = frame.shape[:2]

        if fps <= 0.0 or fps > 240.0:
            fps = 30.0

        if total_frames <= 0:
            total_frames = 1

        duration_seconds = round(total_frames / fps, 2) if (fps > 0 and total_frames > 0) else 0.0

        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

        return {
            "width": width,
            "height": height,
            "fps": fps,
            "total_frames": total_frames,
            "duration_seconds": duration_seconds,
            "codec": codec or "unknown",
        }
    except FileValidationError:
        raise
    except Exception as exc:
        raise FileValidationError(f"Video validation failed: {str(exc)}")
    finally:
        cap.release()
