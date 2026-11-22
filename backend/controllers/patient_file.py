from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload, undefer

from controllers.patient import get_patient_or_404
from models.audit import AuditAction
from models.patient_file import PatientFile, PatientFileFolder, PatientFileVersion
from models.users import User, UserRole
from schemas.patient_file import FileDisplayName, PatientFileResponse, PatientFileUpdate
from services.audit_logger import add_audit_event
from services.patient_files import read_patient_upload


def require_patient_file_access(db: Session, patient_id: int, actor: User, *, lock: bool = False) -> None:
    patient = get_patient_or_404(db, patient_id, lock=lock)
    if actor.role != UserRole.ADMIN and patient.assigned_doctor_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this patient's files.")


def active_files(patient_id: int):
    return (
        select(PatientFile, PatientFileVersion)
        .join(PatientFileVersion, and_(
            PatientFileVersion.file_id == PatientFile.id,
            PatientFileVersion.number == PatientFile.current_version,
        ))
        .where(PatientFile.patient_id == patient_id, PatientFile.deleted_at.is_(None))
        .options(joinedload(PatientFile.uploaded_by).load_only(User.full_name))
    )


def get_active_file(db: Session, patient_id: int, file_id: int, *, include_content: bool = False):
    query = active_files(patient_id).where(PatientFile.id == file_id)
    if include_content:
        query = query.options(undefer(PatientFileVersion.content))
    result = db.execute(query).one_or_none()
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient file not found.")
    return result


def file_response(entry: PatientFile, version: PatientFileVersion) -> PatientFileResponse:
    return PatientFileResponse(
        id=entry.id,
        patient_id=entry.patient_id,
        folder=entry.folder,
        display_name=entry.display_name,
        description=entry.description,
        media_type=version.media_type,
        size_bytes=version.size_bytes,
        version=version.number,
        uploaded_by_id=entry.uploaded_by_id,
        uploaded_by_name=entry.uploaded_by.full_name,
        created_at=entry.created_at.replace(tzinfo=entry.created_at.tzinfo or timezone.utc),
        updated_at=entry.updated_at.replace(tzinfo=entry.updated_at.tzinfo or timezone.utc),
    )


def list_files(
    db: Session, patient_id: int, actor: User, ip_address: str | None,
    *, folder: PatientFileFolder | None, skip: int, limit: int,
) -> list[PatientFileResponse]:
    require_patient_file_access(db, patient_id, actor, lock=True)
    query = active_files(patient_id)
    if folder is not None:
        query = query.where(PatientFile.folder == folder)
    files = [file_response(entry, version) for entry, version in db.execute(
        query.order_by(PatientFile.id.desc()).offset(skip).limit(limit),
    )]
    add_audit_event(db, AuditAction.READ, "patient_file_list", actor.id, patient_id, ip_address,
                    {"patient_id": patient_id})
    db.commit()
    return files


def read_file(db: Session, patient_id: int, file_id: int, actor: User, ip_address: str | None):
    require_patient_file_access(db, patient_id, actor, lock=True)
    entry, version = get_active_file(db, patient_id, file_id, include_content=True)
    result = (entry.display_name, version.media_type, version.content)
    add_audit_event(db, AuditAction.READ, "patient_file", actor.id, file_id, ip_address,
                    {"patient_id": patient_id, "version": version.number})
    db.commit()
    return result


def upload_file(
    db: Session, patient_id: int, actor: User, ip_address: str | None, file: UploadFile,
    *, folder: PatientFileFolder, display_name: str | None, description: str | None,
) -> PatientFileResponse:
    require_patient_file_access(db, patient_id, actor)
    if display_name is None:
        try:
            display_name = TypeAdapter(FileDisplayName).validate_python(file.filename or "patient-file")
        except ValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Supply a valid display name for this file.") from exc
    content, media_type = read_patient_upload(file)

    require_patient_file_access(db, patient_id, actor, lock=True)
    entry = PatientFile(
        patient_id=patient_id, folder=folder, display_name=display_name,
        description=description, uploaded_by=actor,
    )
    db.add(entry)
    db.flush()
    version = append_file_version(db, entry, actor, content, media_type)
    add_audit_event(db, AuditAction.CREATE, "patient_file", actor.id, entry.id, ip_address,
                    {"patient_id": patient_id, "version": version.number})
    result = file_response(entry, version)
    db.commit()
    return result


def append_file_version(
    db: Session, entry: PatientFile, actor: User, content: bytes, media_type: str,
) -> PatientFileVersion:
    version = PatientFileVersion(
        file_id=entry.id, number=entry.current_version, media_type=media_type,
        size_bytes=len(content), content=content, uploaded_by_id=actor.id,
    )
    db.add(version)
    return version


def replace_file(
    db: Session, patient_id: int, file_id: int, actor: User, ip_address: str | None, file: UploadFile,
) -> PatientFileResponse:
    require_patient_file_access(db, patient_id, actor)
    get_active_file(db, patient_id, file_id)
    content, media_type = read_patient_upload(file)

    require_patient_file_access(db, patient_id, actor, lock=True)
    entry, _ = get_active_file(db, patient_id, file_id)
    entry.current_version += 1
    version = append_file_version(db, entry, actor, content, media_type)
    add_audit_event(db, AuditAction.UPDATE, "patient_file", actor.id, file_id, ip_address,
                    {"patient_id": patient_id, "version": version.number})
    db.flush()
    result = file_response(entry, version)
    db.commit()
    return result


def update_file(
    db: Session, patient_id: int, file_id: int, actor: User, ip_address: str | None, data: PatientFileUpdate,
) -> PatientFileResponse:
    require_patient_file_access(db, patient_id, actor, lock=True)
    entry, version = get_active_file(db, patient_id, file_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(entry, field, value)
    add_audit_event(db, AuditAction.UPDATE, "patient_file", actor.id, file_id, ip_address,
                    {"patient_id": patient_id, "fields": sorted(changes)})
    db.flush()
    result = file_response(entry, version)
    db.commit()
    return result


def delete_file(db: Session, patient_id: int, file_id: int, actor: User, ip_address: str | None) -> None:
    require_patient_file_access(db, patient_id, actor, lock=True)
    entry, _ = get_active_file(db, patient_id, file_id)
    entry.deleted_at = datetime.now(timezone.utc)
    entry.deleted_by_id = actor.id
    add_audit_event(db, AuditAction.DELETE, "patient_file", actor.id, file_id, ip_address,
                    {"patient_id": patient_id})
    db.commit()
