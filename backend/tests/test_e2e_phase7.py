import sys
import os
import io
import base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
from decimal import Decimal

try:
    import pytest
except ImportError:
    class _PytestStub:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def skip(reason=""):
            print(f"Skipping test: {reason}")
    pytest = _PytestStub()

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_orthobite.db"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")
os.environ.setdefault("BREVO_API_KEY", "test-key")
os.environ.setdefault("BREVO_SENDER_EMAIL", "test@test.com")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from config.database import Base, get_db
from main import app

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    if os.path.exists("test_orthobite.db"):
        try:
            os.remove("test_orthobite.db")
        except Exception:
            pass


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


state: dict = {}


class TestPhase1Auth:
    def test_patient_register(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Test Patient",
            "username": "testpatient",
            "email": "patient@test.com",
            "phone": "09170000001",
            "password": "Secret123!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "patient"
        state["patient_id"] = data["id"]

    def test_patient_login_returns_jwt(self, client):
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "Secret123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        state["patient_token"] = data["access_token"]

    def test_admin_register(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Admin User",
            "username": "adminuser",
            "email": "admin@test.com",
            "phone": "09170000000",
            "password": "Admin123!",
        })
        assert resp.status_code == 201

        db = TestingSession()
        from models.users import User, UserRole
        user = db.query(User).filter(User.username == "adminuser").first()
        user.role = UserRole.ADMIN
        db.commit()
        db.close()

        resp = client.post("/auth/login", json={
            "identifier": "adminuser",
            "password": "Admin123!",
        })
        assert resp.status_code == 200
        state["admin_token"] = resp.json()["access_token"]

    def test_wrong_password_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "WrongPassword",
        })
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "Secret123!",
        })
        refresh = resp.json()["refresh_token"]
        resp2 = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp2.status_code == 200
        assert "access_token" in resp2.json()


class TestPhase2Doctor:
    def test_doctor_created_and_profile_set(self, client):
        resp = client.post(
            "/users/staff",
            json={
                "full_name": "Dr. Maria Santos",
                "username": "drsantos",
                "email": "drsantos@test.com",
                "phone": "09170000002",
                "password": "Doctor123!",
                "role": "doctor",
            },
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code in (200, 201)
        state["doctor_user_id"] = resp.json()["id"]

        resp2 = client.post("/auth/login", json={
            "identifier": "drsantos",
            "password": "Doctor123!",
        })
        assert resp2.status_code == 200
        state["doctor_token"] = resp2.json()["access_token"]

    def test_set_availability_rules(self, client):
        resp = client.put(
            "/doctors/me/availability",
            json={"rules": [
                {"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00",
                 "slot_duration_minutes": 30, "is_active": True},
            ]},
            headers={"Authorization": f"Bearer {state['doctor_token']}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestPhase3Appointments:
    def test_book_appointment(self, client):
        resp = client.get("/doctors/", headers={"Authorization": f"Bearer {state['patient_token']}"})
        doctors = resp.json()
        assert len(doctors) > 0, "No doctor profiles found"

        state["doctor_profile_id"] = doctors[0]["id"]
        future_start = (datetime.now() + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0
        ).isoformat()
        future_end = (datetime.now() + timedelta(days=3)).replace(
            hour=10, minute=30, second=0, microsecond=0
        ).isoformat()

        resp = client.post(
            "/appointments/",
            json={
                "doctor_id": state["doctor_profile_id"],
                "start_time": future_start,
                "end_time": future_end,
                "reason_for_visit": "Initial consultation",
            },
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code in (200, 201)
        state["appointment_id"] = resp.json()["id"]

    def test_duplicate_booking_rejected(self, client):
        future_start = (datetime.now() + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0
        ).isoformat()
        future_end = (datetime.now() + timedelta(days=3)).replace(
            hour=10, minute=30, second=0, microsecond=0
        ).isoformat()

        resp = client.post(
            "/appointments/",
            json={
                "doctor_id": state["doctor_profile_id"],
                "start_time": future_start,
                "end_time": future_end,
                "reason_for_visit": "Duplicate",
            },
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code in (400, 409)


VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02"
    b"\x08\x06\x00\x00\x00r\xb6\r$\x00\x00\x00\x14IDATx\x9cc\xfc\xcf\xc0"
    b"\xf0\x9f\x81\x81\x81\x81\x89\x01\n\x00\x1f\x17\x02\x02O\x94\xce\xbe"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestPhase4Notifications:
    def test_notification_log_accessible(self, client):
        resp = client.get(
            "/notifications/logs",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data or isinstance(data, list)
        logs = data.get("logs", data) if isinstance(data, dict) else data
        assert any(l.get("status") in ("simulated", "sent") for l in logs)


class TestPhase5Records:
    def test_signature_upload_valid_image(self, client):
        resp = client.post(
            "/records/signatures/upload",
            files={"file": ("signature.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/signatures/")

    def test_signature_upload_invalid_bytes_rejected(self, client):
        resp = client.post(
            "/records/signatures/upload",
            files={"file": ("bad.png", io.BytesIO(b"NOT_A_VALID_IMAGE_FILE"), "image/png")},
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 400

    def test_signature_base64_valid(self, client):
        b64 = "data:image/png;base64," + base64.b64encode(VALID_PNG_BYTES).decode("utf-8")
        resp = client.post(
            "/records/signatures/base64",
            json={"signature_data": b64},
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/signatures/")

    def test_signature_base64_invalid_rejected(self, client):
        b64 = "data:image/png;base64," + base64.b64encode(b"CORRUPTED_NON_IMAGE_DATA").decode("utf-8")
        resp = client.post(
            "/records/signatures/base64",
            json={"signature_data": b64},
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 400

    def test_create_treatment_record(self, client):
        resp = client.post(
            "/records/",
            json={
                "patient_id": state["patient_id"],
                "treatment_name": "Braces Consultation",
                "value_of_work": "5000.00",
                "date": str(date.today()),
            },
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code in (200, 201)
        state["record_id"] = resp.json()["id"]

    def test_add_payment_installment(self, client):
        resp = client.post(
            f"/records/{state['record_id']}/payments",
            json={
                "patient_id": state["patient_id"],
                "amount": "1500.00",
                "method": "Cash",
                "payment_date": str(date.today()),
            },
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code in (200, 201)

    def test_ledger_balance_correct(self, client):
        resp = client.get(
            f"/records/patient/{state['patient_id']}/ledger",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        ledger = resp.json()
        assert float(ledger["total_value_of_work"]) == 5000.00
        assert float(ledger["total_amount_paid"]) == 1500.00
        assert float(ledger["balance_due"]) == 3500.00


class TestPhase6Chat:
    def test_conversation_created(self, client):
        resp = client.get(
            "/chat/conversations",
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code == 200


class TestPhase7Compliance:
    def test_audit_log_created_on_login(self, client):
        resp = client.get(
            "/admin/audit/logs?action=LOGIN",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_audit_log_created_on_failed_login(self, client):
        client.post("/auth/login", json={"identifier": "nobody", "password": "bad"})

        resp = client.get(
            "/admin/audit/logs?action=LOGIN_FAILED",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_audit_log_created_on_record_create(self, client):
        resp = client.get(
            "/admin/audit/logs?resource=treatment_record&action=CREATE",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_non_admin_cannot_view_audit_logs(self, client):
        resp = client.get(
            "/admin/audit/logs",
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code == 403

    def test_admin_analytics_overview(self, client):
        resp = client.get(
            "/admin/analytics/overview",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_patients"] >= 1
        assert "total_doctors" in data
        assert "total_active_appointments" in data

    def test_admin_analytics_appointments(self, client):
        resp = client.get(
            "/admin/analytics/appointments",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert "months" in resp.json()

    def test_admin_analytics_revenue(self, client):
        resp = client.get(
            "/admin/analytics/revenue",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "grand_total_billed" in data
        assert "grand_total_collected" in data
        assert "grand_outstanding" in data
        assert data["grand_total_billed"] >= 5000.0
        assert data["grand_total_collected"] >= 1500.0

    def test_audit_purge_minimum_window(self, client):
        resp = client.delete(
            "/admin/audit/purge?older_than_days=10",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code in (400, 422)

    def test_rate_limit_on_login(self, client):
        for _ in range(15):
            r = client.post("/auth/login", json={
                "identifier": "ratelimit_user",
                "password": "WrongPassword",
            })
            if r.status_code == 429:
                break
        assert r.status_code == 429


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine_test)
    test_classes = [
        TestPhase1Auth,
        TestPhase2Doctor,
        TestPhase3Appointments,
        TestPhase4Notifications,
        TestPhase5Records,
        TestPhase6Chat,
        TestPhase7Compliance,
    ]

    passed = 0
    failed = 0
    total = 0

    print("Running OrthoBite End-to-End QA Test Suite...\n" + "=" * 50)
    with TestClient(app) as test_client:
        for cls in test_classes:
            instance = cls()
            methods = [m for m in cls.__dict__ if m.startswith("test_")]
            print(f"\n[{cls.__name__}]")
            for m in methods:
                total += 1
                try:
                    getattr(instance, m)(test_client)
                    print(f"  PASS: {m}")
                    passed += 1
                except Exception as e:
                    print(f"  FAIL: {m} -> {e}")
                    failed += 1

    Base.metadata.drop_all(bind=engine_test)
    if os.path.exists("test_orthobite.db"):
        try:
            os.remove("test_orthobite.db")
        except Exception:
            pass

    print("\n" + "=" * 50)
    print(f"Summary: {passed}/{total} Passed, {failed} Failed.")
    sys.exit(0 if failed == 0 else 1)
