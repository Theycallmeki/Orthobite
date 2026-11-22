import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from config.database import Base, get_db
from config.settings import settings
from controllers.auth import create_access_token
from models.audit import AuditLog
from models.patient_file import PatientFile, PatientFileVersion
from models.users import User, UserRole
from routes.patient import router as patient_router
from routes.patient_file import router as file_router
from services.patient_files import MAX_MULTIPART_BODY_BYTES, MAX_PATIENT_FILE_SIZE_BYTES


def png(color: str) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (2, 2), color).save(stream, "PNG")
    return stream.getvalue()


def pdf() -> bytes:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(stream)
    return stream.getvalue()


@pytest.fixture
def clinic(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "patient-file-integration-test-key")
    postgres_url = os.environ.get("ORTHOBITE_FILES_TEST_POSTGRES_URL")
    schema = f"patient_files_test_{uuid4().hex}"
    if postgres_url:
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'files.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)

    app = FastAPI()
    app.include_router(patient_router)
    app.include_router(file_router)

    def test_db():
        with session() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    roles = {
        "admin": UserRole.ADMIN,
        "doctor": UserRole.DOCTOR,
        "ortho": UserRole.ORTHODONTIST,
        "secretary": UserRole.SECRETARY,
        "patient": UserRole.PATIENT,
    }
    with session() as db:
        users = {
            name: User(username=name, email=f"{name}@example.com", full_name=name.title(),
                       hashed_password="unused", role=role)
            for name, role in roles.items()
        }
        db.add_all(users.values())
        db.flush()
        ids = {name: user.id for name, user in users.items()}
        headers = {
            name: {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}
            for name, user in users.items()
        }
        db.commit()

    try:
        with TestClient(app) as client:
            yield client, session, ids, headers
    finally:
        if postgres_url:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


def create_profile(client, headers, assigned_doctor_id=None):
    response = client.post("/patients/", headers=headers, json={"assigned_doctor_id": assigned_doctor_id})
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] is None
    return f"/patients/{response.json()['id']}"


def test_file_lifecycle_and_retention(clinic):
    client, session, ids, headers = clinic
    profile = create_profile(client, headers["admin"], ids["doctor"])
    files = f"{profile}/files"
    original = png("red")
    uploaded = client.post(files, headers=headers["doctor"], data={"folder": "xrays"},
                           files={"file": ("panoramic.png", original, "application/octet-stream")})
    assert uploaded.status_code == 201, uploaded.text
    item = uploaded.json()
    file_id = item["id"]
    file_url = f"{files}/{file_id}"
    assert item["media_type"] == "image/png"
    assert item["uploaded_by_name"] == "Doctor"
    assert item["size_bytes"] == len(original)
    assert item["display_name"] == "panoramic.png"
    assert datetime.fromisoformat(item["created_at"]).tzinfo is not None

    edited = client.patch(file_url, headers=headers["doctor"], json={
        "display_name": "Panorámic X-ray.png", "folder": "other", "description": "Baseline",
    })
    assert edited.status_code == 200, edited.text
    assert edited.json()["description"] == "Baseline"
    assert client.get(files, headers=headers["doctor"], params={"folder": "xrays"}).json() == []
    listed = client.get(files, headers=headers["doctor"], params={"folder": "other"})
    assert listed.json() == [edited.json()]
    assert listed.headers["cache-control"] == "private, no-store"

    preview = client.get(f"{file_url}/content", headers=headers["doctor"], params={"preview": True})
    assert preview.content == original
    assert preview.headers["cache-control"] == "private, no-store"
    assert preview.headers["content-disposition"].startswith("inline;")
    assert "Panor%C3%A1mic%20X-ray.png" in preview.headers["content-disposition"]

    document = pdf()
    replaced = client.post(f"{file_url}/versions", headers=headers["doctor"],
                           files={"file": ("consent.pdf", document, "application/pdf")})
    assert replaced.status_code == 201, replaced.text
    assert replaced.json()["version"] == 2
    download = client.get(f"{file_url}/content?preview=true", headers=headers["doctor"])
    assert download.content == document
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert "Panor%C3%A1mic%20X-ray.pdf" in download.headers["content-disposition"]

    assert client.delete(file_url, headers=headers["doctor"]).status_code == 204
    assert client.get(files, headers=headers["doctor"]).json() == []
    assert client.get(f"{file_url}/content", headers=headers["admin"]).status_code == 404
    assert client.delete(profile, headers=headers["admin"]).status_code == 409

    with session() as db:
        assert db.get(PatientFile, file_id).deleted_by_id == ids["doctor"]
        assert db.get(PatientFileVersion, (file_id, 1)).content == original
        assert db.get(PatientFileVersion, (file_id, 2)).content == document
        audit = db.scalars(select(AuditLog).where(AuditLog.resource == "patient_file").order_by(AuditLog.id)).all()
        assert [event.action.value for event in audit] == ["CREATE", "UPDATE", "READ", "UPDATE", "READ", "DELETE"]
        assert {event.actor_id for event in audit} == {ids["doctor"]}
        assert {event.extra["patient_id"] for event in audit} == {item["patient_id"]}


def test_access_uses_current_assignment_and_patient_id(clinic):
    client, _, ids, headers = clinic
    profile = create_profile(client, headers["admin"])
    files = f"{profile}/files"
    assert client.get(files).status_code == 401
    assert client.get(files, headers=headers["admin"]).json() == []
    for name in ("doctor", "ortho", "secretary", "patient"):
        assert client.get(files, headers=headers[name]).status_code == 403

    change = {"assigned_doctor_id": ids["doctor"]}
    assert client.post("/patients/", headers=headers["doctor"], json=change).status_code == 403
    assert client.patch(profile, headers=headers["doctor"], json=change).status_code == 403
    assert client.patch(profile, headers=headers["admin"], json={
        "assigned_doctor_id": ids["secretary"],
    }).status_code == 422
    assert client.patch(profile, headers=headers["secretary"], json={"notes": "Follow-up"}).status_code == 200
    assert client.patch(profile, headers=headers["admin"], json=change).status_code == 200

    upload = {"file": ("xray.png", png("red"), "image/png")}
    original = client.post(files, headers=headers["doctor"], data={"folder": "xrays"}, files=upload)
    assert original.status_code == 201, original.text
    file_id = original.json()["id"]
    other = create_profile(client, headers["admin"], ids["doctor"])
    assert client.get(f"{other}/files/{file_id}/content", headers=headers["doctor"]).status_code == 404
    assert client.delete(f"{other}/files/{file_id}", headers=headers["doctor"]).status_code == 404
    assert client.delete(other, headers=headers["admin"]).status_code == 200

    assert client.patch(profile, headers=headers["admin"], json={"assigned_doctor_id": ids["ortho"]}).status_code == 200
    assert client.get(f"{files}/{file_id}/content", headers=headers["doctor"]).status_code == 403
    assert client.post(files, headers=headers["doctor"], data={"folder": "xrays"}, files=upload).status_code == 403
    assert client.get(f"{files}/{file_id}/content", headers=headers["ortho"]).status_code == 200


def test_invalid_uploads_leave_current_version_available(clinic):
    client, _, ids, headers = clinic
    profile = create_profile(client, headers["admin"], ids["doctor"])
    files = f"{profile}/files"
    actor = headers["doctor"]
    valid = pdf()
    response = client.post(files, headers=actor, data={"folder": "contracts-consent"},
                           files={"file": ("contract.pdf", valid, "application/pdf")})
    assert response.status_code == 201, response.text
    file_url = f"{files}/{response.json()['id']}"

    for invalid, code in ((b"%PDF-1.7\nfake\n%%EOF", 400), (b"", 400),
                          (b"X" * (MAX_PATIENT_FILE_SIZE_BYTES + 1), 413),
                          (b"X" * MAX_MULTIPART_BODY_BYTES, 413)):
        rejected = client.post(f"{file_url}/versions", headers=actor,
                               files={"file": ("replacement.pdf", invalid, "application/pdf")})
        assert rejected.status_code == code, rejected.text
    for invalid_name in ("../contract.pdf", " ", None):
        assert client.patch(file_url, headers=actor, json={"display_name": invalid_name}).status_code == 422
    assert client.patch(file_url, headers=actor, json={"description": "Invalid\x00note"}).status_code == 422
    description = "\U0001F4C4" * 2000
    updated = client.patch(file_url, headers={**actor, "Content-Type": "application/json"},
                           content=json.dumps({"description": description}))
    assert updated.status_code == 200
    assert updated.json()["description"] == description
    invalid_form = client.post(files, headers=actor, data={"folder": "xrays", "display_name": "../xray.png"},
                               files={"file": ("xray.png", png("red"), "image/png")})
    assert invalid_form.status_code == 422
    assert client.get(files, headers=actor).json()[0]["version"] == 1
    assert client.get(f"{file_url}/content", headers=actor).content == valid


def test_concurrent_replacements_preserve_both_versions(clinic):
    client, session, ids, headers = clinic
    profile = create_profile(client, headers["admin"], ids["doctor"])
    files = f"{profile}/files"
    actor = headers["doctor"]
    upload = client.post(files, headers=actor, data={"folder": "xrays"},
                         files={"file": ("original.png", png("red"), "image/png")})
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]
    replacements = {png("blue"), png("green")}

    def replace(content):
        return client.post(f"{files}/{file_id}/versions", headers=actor,
                           files={"file": ("replacement.png", content, "image/png")})

    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(replace, replacements))
    assert [response.status_code for response in responses] == [201, 201]
    assert {response.json()["version"] for response in responses} == {2, 3}
    with session() as db:
        assert {db.get(PatientFileVersion, (file_id, n)).content for n in (2, 3)} == replacements
