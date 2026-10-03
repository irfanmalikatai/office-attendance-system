from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now
    )

    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="employee"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    check_out: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="attendance_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "work_date",
            name="uq_employee_work_date"
        ),
    )