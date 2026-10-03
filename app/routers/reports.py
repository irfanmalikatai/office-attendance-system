import csv
import io
import calendar

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, AttendanceRecord
from app.config import get_now
from app.rules import get_worked_hours
from app.routers.employees import verify_admin


router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get(
    "/monthly",
    dependencies=[Depends(verify_admin)]
)
def monthly_report(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    now=Depends(get_now)
):
    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "date",
        "code",
        "name",
        "check-in",
        "check-out",
        "hours worked",
        "status"
    ])

    # Month ki start/end date
    _, days_in_month = calendar.monthrange(year, month)

    # Month ke attendance records
    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.work_date >= f"{year:04d}-{month:02d}-01",
        AttendanceRecord.work_date <= f"{year:04d}-{month:02d}-{days_in_month:02d}"
    ).all()

    # Agar month mein koi attendance record hi nahi
    # to sirf CSV header return karo
    if not records:
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f"attachment; filename=monthly_report_{year}_{month}.csv"
            }
        )

    employees = db.query(Employee).all()

    for day in range(1, days_in_month + 1):

        current_date = now.date().replace(
            year=year,
            month=month,
            day=day
        )

        # Saturday / Sunday skip
        if current_date.weekday() >= 5:
            continue

        for employee in employees:

            record = db.query(AttendanceRecord).filter(
                AttendanceRecord.employee_id == employee.id,
                AttendanceRecord.work_date == current_date
            ).first()

            if record is None:

                writer.writerow([
                    current_date,
                    employee.employee_code,
                    employee.full_name,
                    "",
                    "",
                    "",
                    "Absent"
                ])

                continue

            check_in = record.check_in.strftime("%H:%M")

            check_out = (
                record.check_out.strftime("%H:%M")
                if record.check_out
                else ""
            )

            if record.check_out is None:

                status = "Missing Check-Out"
                hours_worked = ""

            else:

                hours_worked = get_worked_hours(
                    record.check_in,
                    record.check_out
                )

                if hours_worked < 4:
                    status = "Half Day"
                else:
                    status = "Present"

            writer.writerow([
                current_date,
                employee.employee_code,
                employee.full_name,
                check_in,
                check_out,
                hours_worked,
                status
            ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename=monthly_report_{year}_{month}.csv"
        }
    )
