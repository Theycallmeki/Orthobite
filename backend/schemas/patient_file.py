from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, field_validator

from models.patient_file import PatientFileFolder


def validate_display_name(name: str) -> str:
    if not name.strip(" .") or any(char in '<>:"/\\|?*' or not char.isprintable() for char in name):
        raise ValueError("Enter a file name without path separators, reserved characters, or control characters.")
    return name


FileDisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    AfterValidator(validate_display_name),
]
FileDescription = Annotated[str, StringConstraints(max_length=2000, pattern=r"^[^\x00]*$")]


class PatientFileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: FileDisplayName | None = None
    description: FileDescription | None = None
    folder: PatientFileFolder | None = None

    @field_validator("display_name", "folder")
    @classmethod
    def require_value_when_set(cls, value):
        if value is None:
            raise ValueError("This field needs a value when supplied.")
        return value


class PatientFileResponse(BaseModel):
    id: int
    patient_id: int
    folder: PatientFileFolder
    display_name: str
    description: str | None
    media_type: str
    size_bytes: int
    version: int
    uploaded_by_id: int
    uploaded_by_name: str
    created_at: datetime
    updated_at: datetime
