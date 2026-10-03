import bcrypt
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import get_now, settings
from app.database import get_db
from app.models import Employee, AttendanceRecord
from app.schemas import (
    AttendancePunchRequest,
    AttendanceCheckInResponse,
    AttendanceCheckOutResponse,
    TodayAttendanceResponse
)
from app.rules import (
    get_attendance_status,
    get_worked_hours,
    get_checkout_status,
    get_absent_status
)
from app.routers.employees import verify_admin


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)


@router.post(
    "/check-in",
    response_model=AttendanceCheckInResponse
)
def check_in(
    body: AttendancePunchRequest,
    now=Depends(get_now),
    db: Session = Depends(get_db)
):
    # Employee find karo
    employee = db.query(Employee).filter(
        Employee.employee_code == body.employee_code
    ).first()

    # Wrong employee code
    if not employee:
        raise HTTPException(
            status_code=401,
            detail="Invalid code or PIN"
        )

    # Inactive employee
    if not employee.is_active:
        raise HTTPException(
            status_code=403,
            detail="Employee is inactive"
        )

    # PIN verify karo
    valid_pin = bcrypt.checkpw(
        body.pin.encode("utf-8"),
        employee.pin_hash.encode("utf-8")
    )

    if not valid_pin:
        raise HTTPException(
            status_code=401,
            detail="Invalid code or PIN"
        )

    # Aaj ka attendance record check karo
    existing_record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == employee.id,
        AttendanceRecord.work_date == now.date()
    ).first()

    if existing_record:
        check_in_time = existing_record.check_in.strftime("%H:%M")

        raise HTTPException(
            status_code=409,
            detail=f"Already checked in at {check_in_time}"
        )

    # Office start time
    office_start_hour, office_start_minute = map(
        int,
        settings.office_start.split(":")
    )

    office_start_minutes = (
        office_start_hour * 60
        + office_start_minute
    )

    current_minutes = (
        now.hour * 60
        + now.minute
    )

    status = get_attendance_status(
    current_minutes,
    office_start_minutes,
    settings.grace_minutes
    )

    # Attendance record create karo
    record = AttendanceRecord(
        employee_id=employee.id,
        work_date=now.date(),
        check_in=now
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "name": employee.full_name,
        "check_in": now.strftime("%H:%M"),
        "status": status
    }

@router.post(
    "/check-out",
    response_model=AttendanceCheckOutResponse
)
def check_out(
    body: AttendancePunchRequest,
    now=Depends(get_now),
    db: Session = Depends(get_db)
):
    # Employee find karo
    employee = db.query(Employee).filter(
        Employee.employee_code == body.employee_code
    ).first()

    # Wrong employee code
    if not employee:
        raise HTTPException(
            status_code=401,
            detail="Invalid code or PIN"
        )

    # Inactive employee
    if not employee.is_active:
        raise HTTPException(
            status_code=403,
            detail="Employee is inactive"
        )

    # PIN verify karo
    valid_pin = bcrypt.checkpw(
        body.pin.encode("utf-8"),
        employee.pin_hash.encode("utf-8")
    )

    if not valid_pin:
        raise HTTPException(
            status_code=401,
            detail="Invalid code or PIN"
        )

    # Aaj ka attendance record find karo
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == employee.id,
        AttendanceRecord.work_date == now.date()
    ).first()

    # Check-in nahi kiya
    if not record:
        raise HTTPException(
            status_code=409,
            detail="Please check in first"
        )

    # Already checked out
    if record.check_out is not None:
        check_out_time = record.check_out.strftime("%H:%M")

        raise HTTPException(
            status_code=409,
            detail=f"Already checked out at {check_out_time}"
        )

    # Check-in ko timezone-aware banao
    check_in_time = record.check_in.replace(
        tzinfo=now.tzinfo
    )

    # Check-out save karo
    record.check_out = now

    worked_hours = get_worked_hours(
    check_in_time,
    now
    )

    status = get_checkout_status(
        worked_hours,
        settings.half_day_hours
    )

    db.commit()
    db.refresh(record)

    return {
        "name": employee.full_name,
        "check_in": record.check_in.strftime("%H:%M"),
        "check_out": now.strftime("%H:%M"),
        "status": status
    }
@router.get(
    "/today",
    response_model=TodayAttendanceResponse,
    dependencies=[Depends(verify_admin)]
)
def today_attendance(
    now=Depends(get_now),
    db: Session = Depends(get_db)
):
    # Admin key check
    # NOTE: apne existing admin-key check ka same pattern use karo
    today = now.date()

    employees = db.query(Employee).filter(
        Employee.is_active == True
    ).all()

    result = []

    present_count = 0
    late_count = 0
    absent_count = 0

    for employee in employees:

        record = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.work_date == today
        ).first()

        # No attendance record
        if record is None:

            # Saturday / Sunday = not absent
            if today.weekday() >= 5:
                status = "Not Working"
            else:
                status = get_absent_status(False)
                absent_count += 1

            result.append({
                "employee_code": employee.employee_code,
                "name": employee.full_name,
                "check_in": None,
                "check_out": None,
                "status": status
            })

            continue

        check_in = record.check_in.strftime("%H:%M")

        check_out = (
            record.check_out.strftime("%H:%M")
            if record.check_out
            else None
        )

        # Employee checked out
        if record.check_out is not None:

            worked_hours = get_worked_hours(
                record.check_in,
                record.check_out
            )

            status = get_checkout_status(
                worked_hours,
                settings.half_day_hours
            )

            present_count += 1

        # Employee checked in but hasn't checked out
        else:

            office_start_hour, office_start_minute = map(
                int,
                settings.office_start.split(":")
            )

            office_start_minutes = (
                office_start_hour * 60
                + office_start_minute
            )

            check_in_minutes = (
                record.check_in.hour * 60
                + record.check_in.minute
            )

            status = get_attendance_status(
                check_in_minutes,
                office_start_minutes,
                settings.grace_minutes
            )

            if status == "Late":
                late_count += 1
            else:
                present_count += 1

        result.append({
            "employee_code": employee.employee_code,
            "name": employee.full_name,
            "check_in": check_in,
            "check_out": check_out,
            "status": status
        })

    return {
        "date": str(today),
        "employees": result,
        "totals": {
            "present": present_count,
            "late": late_count,
            "absent": absent_count
        }
    }