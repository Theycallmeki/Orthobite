from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from config.database import get_db
from controllers import patient_file as files
from dependencies import require_doctor
from models.patient_file import PatientFileFolder
from models.users import User
from schemas.patient_file import FileDescription, FileDisplayName, PatientFileResponse, PatientFileUpdate
from services.patient_files import MAX_MULTIPART_BODY_BYTES, patient_file_disposition


router = APIRouter(
    prefix="/patients/{patient_id}/files",
    tags=["Patient Files"],
    max_body_size=MAX_MULTIPART_BODY_BYTES,
    form_limits={"max_files": 1, "max_fields": 3, "max_part_size": 8192},
)
DbSession = Annotated[Session, Depends(get_db)]
FileActor = Annotated[User, Depends(require_doctor)]
PRIVATE_HEADERS = {"Cache-Control": "private, no-store"}


def request_address(request: Request, response: Response) -> str | None:
    response.headers.update(PRIVATE_HEADERS)
    return request.client.host if request.client else None


ClientAddress = Annotated[str | None, Depends(request_address)]


@router.get("", response_model=list[PatientFileResponse])
def list_patient_files(
    patient_id: int, db: DbSession, actor: FileActor, ip_address: ClientAddress,
    folder: PatientFileFolder | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return files.list_files(db, patient_id, actor, ip_address, folder=folder, skip=skip, limit=limit)


@router.post("", response_model=PatientFileResponse, status_code=status.HTTP_201_CREATED)
def upload_patient_file(
    patient_id: int, db: DbSession, actor: FileActor, ip_address: ClientAddress,
    file: Annotated[UploadFile, File()],
    folder: Annotated[PatientFileFolder, Form()],
    display_name: Annotated[FileDisplayName | None, Form()] = None,
    description: Annotated[FileDescription | None, Form()] = None,
):
    return files.upload_file(
        db, patient_id, actor, ip_address, file,
        folder=folder, display_name=display_name, description=description,
    )


@router.get("/{file_id}/content", response_class=Response)
def get_patient_file_content(
    patient_id: int, file_id: int, db: DbSession, actor: FileActor, ip_address: ClientAddress,
    preview: bool = False,
):
    display_name, media_type, content = files.read_file(db, patient_id, file_id, actor, ip_address)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            **PRIVATE_HEADERS,
            "Content-Disposition": patient_file_disposition(display_name, media_type, preview=preview),
        },
    )


@router.patch("/{file_id}", response_model=PatientFileResponse, max_body_size=32 * 1024)
def update_patient_file(
    patient_id: int, file_id: int, data: PatientFileUpdate,
    db: DbSession, actor: FileActor, ip_address: ClientAddress,
):
    return files.update_file(db, patient_id, file_id, actor, ip_address, data)


@router.post("/{file_id}/versions", response_model=PatientFileResponse, status_code=status.HTTP_201_CREATED)
def replace_patient_file(
    patient_id: int, file_id: int, db: DbSession, actor: FileActor, ip_address: ClientAddress,
    file: Annotated[UploadFile, File()],
):
    return files.replace_file(db, patient_id, file_id, actor, ip_address, file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_file(patient_id: int, file_id: int, db: DbSession, actor: FileActor, ip_address: ClientAddress):
    files.delete_file(db, patient_id, file_id, actor, ip_address)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=PRIVATE_HEADERS)
