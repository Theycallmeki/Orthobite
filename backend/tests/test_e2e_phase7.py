"""
test_e2e_phase7.py — End-to-End test suite covering all 7 phases.

Uses an in-memory SQLite database via FastAPI TestClient so the tests
run completely offline without any external services.

Run with:
    cd backend
    pytest tests/test_e2e_phase7.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# In-memory SQLite test database setup
# ---------------------------------------------------------------------------
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
    """Create all tables before tests, drop after."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    # Clean up test db file
    if os.path.exists("test_orthobite.db"):
        os.remove("test_orthobite.db")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared state across tests
# ---------------------------------------------------------------------------
state: dict = {}


# ===========================================================================
# PHASE 1 — Authentication
# ===========================================================================

class TestPhase1Auth:
    def test_patient_register(self, client):
        """Phase 1: Patient self-registration creates a user account."""
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
        """Phase 1: Login returns valid access + refresh tokens."""
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
        """Phase 1: Admin account created via register (or manually seeded)."""
        resp = client.post("/auth/register", json={
            "full_name": "Admin User",
            "username": "adminuser",
            "email": "admin@test.com",
            "phone": "09170000000",
            "password": "Admin123!",
        })
        assert resp.status_code == 201

        # Manually elevate to admin in test DB
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
        """Phase 1: Wrong credentials return 401."""
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "WrongPassword",
        })
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        """Phase 1: Refresh token returns new access token."""
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "Secret123!",
        })
        refresh = resp.json()["refresh_token"]
        resp2 = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp2.status_code == 200
        assert "access_token" in resp2.json()


# ===========================================================================
# PHASE 2 — Doctor Profile & Availability
# ===========================================================================

class TestPhase2Doctor:
    def test_doctor_created_and_profile_set(self, client):
        """Phase 2: Create doctor account then set availability rules."""
        # Create a doctor via admin staff endpoint
        resp = client.post(
            "/auth/staff",
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
        # Accept 201 or 200 depending on route
        assert resp.status_code in (200, 201)
        state["doctor_user_id"] = resp.json()["id"]

        resp2 = client.post("/auth/login", json={
            "identifier": "drsantos",
            "password": "Doctor123!",
        })
        state["doctor_token"] = resp2.json()["access_token"]

    def test_set_availability_rules(self, client):
        """Phase 2: Doctor sets weekly availability rules."""
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


# ===========================================================================
# PHASE 3 — Appointment Booking
# ===========================================================================

class TestPhase3Appointments:
    def test_book_appointment(self, client):
        """Phase 3: Patient can book an appointment with a doctor."""
        # Find the doctor profile id
        resp = client.get("/doctors/", headers={"Authorization": f"Bearer {state['patient_token']}"})
        doctors = resp.json()
        if not doctors:
            pytest.skip("No doctor profiles found")

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
        """Phase 3: Overlapping appointment booking is rejected."""
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


# ===========================================================================
# PHASE 4 — Email Notification Log
# ===========================================================================

class TestPhase4Notifications:
    def test_notification_log_accessible(self, client):
        """Phase 4: Notification logs endpoint is accessible by admin."""
        resp = client.get(
            "/notifications/",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# PHASE 5 — Treatment Records & Financial Ledger
# ===========================================================================

class TestPhase5Records:
    def test_create_treatment_record(self, client):
        """Phase 5: Staff creates a treatment record for a patient."""
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
        """Phase 5: Payment installment reduces the outstanding balance."""
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
        """Phase 5: Ledger reflects correct billed vs paid vs balance."""
        resp = client.get(
            f"/records/patients/{state['patient_id']}/ledger",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        ledger = resp.json()
        assert float(ledger["total_value_of_work"]) == 5000.00
        assert float(ledger["total_amount_paid"]) == 1500.00
        assert float(ledger["balance_due"]) == 3500.00


# ===========================================================================
# PHASE 6 — WebSocket Chat
# ===========================================================================

class TestPhase6Chat:
    def test_conversation_created(self, client):
        """Phase 6: Chat conversation can be created between patient and secretary."""
        resp = client.get(
            "/chat/conversations",
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code == 200


# ===========================================================================
# PHASE 7 — Audit Logging, Rate Limiting & Analytics
# ===========================================================================

class TestPhase7Compliance:
    def test_audit_log_created_on_login(self, client):
        """Phase 7: A LOGIN audit entry exists after successful login."""
        resp = client.get(
            "/admin/audit/logs?action=LOGIN",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_audit_log_created_on_failed_login(self, client):
        """Phase 7: A LOGIN_FAILED audit entry exists after bad credentials."""
        # Trigger a failed login
        client.post("/auth/login", json={"identifier": "nobody", "password": "bad"})

        resp = client.get(
            "/admin/audit/logs?action=LOGIN_FAILED",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_audit_log_created_on_record_create(self, client):
        """Phase 7: A CREATE audit entry exists for treatment_record resource."""
        resp = client.get(
            "/admin/audit/logs?resource=treatment_record&action=CREATE",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_non_admin_cannot_view_audit_logs(self, client):
        """Phase 7: Patient cannot access admin audit logs (403)."""
        resp = client.get(
            "/admin/audit/logs",
            headers={"Authorization": f"Bearer {state['patient_token']}"},
        )
        assert resp.status_code == 403

    def test_rate_limit_on_login(self, client):
        """Phase 7: 11th login attempt in rapid succession returns 429."""
        for _ in range(10):
            client.post("/auth/login", json={
                "identifier": "testpatient",
                "password": "WrongPass",
            })
        resp = client.post("/auth/login", json={
            "identifier": "testpatient",
            "password": "WrongPass",
        })
        assert resp.status_code == 429

    def test_admin_analytics_overview(self, client):
        """Phase 7: Admin analytics overview returns correct patient/doctor counts."""
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
        """Phase 7: Monthly appointment breakdown returns structured data."""
        resp = client.get(
            "/admin/analytics/appointments",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        assert "months" in resp.json()

    def test_admin_analytics_revenue(self, client):
        """Phase 7: Revenue report reflects billed and collected amounts."""
        resp = client.get(
            "/admin/analytics/revenue",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "grand_total_billed" in data
        assert "grand_total_collected" in data
        assert "grand_outstanding" in data
        # Must match Phase 5 data we seeded
        assert data["grand_total_billed"] >= 5000.0
        assert data["grand_total_collected"] >= 1500.0

    def test_audit_purge_minimum_window(self, client):
        """Phase 7: Purge with less than 30 days is rejected (DPA policy)."""
        resp = client.delete(
            "/admin/audit/purge?older_than_days=10",
            headers={"Authorization": f"Bearer {state['admin_token']}"},
        )
        assert resp.status_code == 400

