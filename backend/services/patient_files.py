from io import BytesIO
from urllib.parse import quote

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from services.images import validate_image_bytes


MAX_PATIENT_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_MULTIPART_BODY_BYTES = MAX_PATIENT_FILE_SIZE_BYTES + 64 * 1024

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MEDIA_EXTENSIONS = {media_type: extension for extension, media_type in MEDIA_TYPES.items()}


def read_patient_upload(file: UploadFile) -> tuple[bytes, str]:
    content = file.file.read(MAX_PATIENT_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_PATIENT_FILE_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Files must be 10 MB or smaller.")
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is empty.")

    if content.startswith(b"%PDF-"):
        # Check document structure while preserving the exact uploaded bytes for signed PDFs.
        try:
            pdf = PdfReader(BytesIO(content), strict=True)
            if pdf.is_encrypted or len(pdf.pages) == 0:
                raise ValueError("Expected an unencrypted PDF with at least one page.")
        except Exception as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a valid, unencrypted PDF.") from exc
        return content, MEDIA_TYPES[".pdf"]

    try:
        extension = validate_image_bytes(content, max_size_bytes=MAX_PATIENT_FILE_SIZE_BYTES)
    except HTTPException as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a valid PDF, JPEG, PNG, or WebP file.") from exc
    return content, MEDIA_TYPES[extension]


def patient_file_disposition(display_name: str, media_type: str, *, preview: bool) -> str:
    extension = MEDIA_EXTENSIONS[media_type]
    name = display_name.rstrip(" .")
    stem, _, suffix = name.rpartition(".")
    if stem and f".{suffix.lower()}" in {*MEDIA_TYPES, ".jpeg"}:
        name = stem.rstrip(" .") or "patient-file"
    filename = quote(f"{name}{extension}", safe="")
    disposition = "inline" if preview and media_type.startswith("image/") else "attachment"
    return f"{disposition}; filename=\"patient-file{extension}\"; filename*=UTF-8''{filename}"
