from datetime import datetime
from zoneinfo import ZoneInfo

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.config import get_now, settings
from app.models import Employee, AttendanceRecord


# Test database
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()


def create_employee(
    db,
    employee_code="ES-001",
    pin="1234",
    is_active=True
):
    pin_hash = bcrypt.hashpw(
        pin.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    employee = Employee(
        employee_code=employee_code,
        full_name="Ali",
        department="IT",
        pin_hash=pin_hash,
        is_active=is_active
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


def set_time(year, month, day, hour, minute):
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=ZoneInfo("Asia/Karachi")
    )


def test_check_in_present(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 8, 55)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Ali"
    assert data["check_in"] == "08:55"
    assert data["status"] == "Present"

def test_check_in_at_grace_limit(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 9, 15)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Present"

def test_check_in_late(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 9, 16)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Late"

def test_wrong_pin(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "9999"
        }
    )

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid code or PIN"

    records = db.query(AttendanceRecord).all()

    assert len(records) == 0

def test_unknown_employee_code(client, db):
    fake_time = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-999",
            "pin": "1234"
        }
    )

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid code or PIN"

def test_inactive_employee(client, db):
    create_employee(
        db,
        is_active=False
    )

    fake_time = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 403

    assert response.json()["detail"] == "Employee is inactive"

    records = db.query(AttendanceRecord).all()

    assert len(records) == 0

def test_double_check_in(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: fake_time

    first_response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert second_response.status_code == 409

    assert "Already checked in" in second_response.json()["detail"]


def test_check_out_without_check_in(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 2, 18, 0)

    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.post(
        "/attendance/check-out",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 409

    assert response.json()["detail"] == "Please check in first"

def test_half_day(client, db):
    create_employee(db)

    check_in_time = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: check_in_time

    check_in_response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert check_in_response.status_code == 200

    check_out_time = set_time(2026, 10, 2, 12, 0)

    app.dependency_overrides[get_now] = lambda: check_out_time

    check_out_response = client.post(
        "/attendance/check-out",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert check_out_response.status_code == 200

    data = check_out_response.json()

    assert data["check_in"] == "09:00"
    assert data["check_out"] == "12:00"
    assert data["status"] == "Half Day"


def test_admin_endpoint_without_key(client):
    response = client.get("/employees")

    assert response.status_code == 401

def test_yesterday_missing_check_out(client, db):
    create_employee(db)

    # Yesterday: employee checks in
    yesterday = set_time(2026, 10, 2, 9, 0)

    app.dependency_overrides[get_now] = lambda: yesterday

    response = client.post(
        "/attendance/check-in",
        json={
            "employee_code": "ES-001",
            "pin": "1234"
        }
    )

    assert response.status_code == 200

    # Today
    today = set_time(2026, 10, 3, 10, 0)

    app.dependency_overrides[get_now] = lambda: today

    response = client.get(
        "/reports/monthly",
        params={
            "year": 2026,
            "month": 10
        },
        headers={
            "X-Admin-Key": "my-secret-admin-key"
        }
    )

    assert response.status_code == 200

    csv_text = response.text

    assert "Missing Check-Out" in csv_text

def test_tuesday_absent(client, db):
    create_employee(db)

    fake_time = set_time(2026, 10, 6, 10, 0)
    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.get(
        "/attendance/today",
        headers={
            "X-Admin-Key": settings.admin_key
        }
    )

    assert response.status_code == 200

    data = response.json()

    employee = next(
        item for item in data["employees"]
        if item["employee_code"] == "ES-001"
    )

    assert employee["status"] == "Absent"

def test_saturday_not_absent(client, db):
    create_employee(db)

    # Saturday: 2026-10-03
    fake_time = set_time(2026, 10, 3, 10, 0)
    app.dependency_overrides[get_now] = lambda: fake_time

    response = client.get(
        "/attendance/today",
        headers={
            "X-Admin-Key": settings.admin_key
        }
    )

    assert response.status_code == 200

    data = response.json()

    employee = next(
        item for item in data["employees"]
        if item["employee_code"] == "ES-001"
    )

    assert employee["status"] != "Absent"
def test_empty_month_csv(client, db):
    create_employee(db)

    response = client.get(
        "/reports/monthly",
        params={
            "year": 2025,
            "month": 1
        },
        headers={
            "X-Admin-Key": settings.admin_key
        }
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip().splitlines()

    assert len(lines) == 1

    assert lines[0] == "date,code,name,check-in,check-out,hours worked,status"