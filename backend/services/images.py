import io

from fastapi import HTTPException, status
from PIL import Image


ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


def validate_image_bytes(data: bytes) -> str:
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image data cannot be empty.",
        )
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image size exceeds the maximum allowed limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB.",
        )
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        fmt = (image.format or "").upper()
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format: '{fmt or 'unknown'}'. Allowed formats: PNG, JPEG, WEBP.",
            )
        return ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupted or invalid image data: {str(e)}",
        )
