from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    department: str
    pin: str = Field(pattern=r"^\d{4}$")


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    pin: str | None = Field(default=None, pattern=r"^\d{4}$")
    is_active: bool | None = None


class EmployeeResponse(BaseModel):
    id: int
    employee_code: str
    full_name: str
    department: str
    is_active: bool

    model_config = {
        "from_attributes": True
    }
class AttendancePunchRequest(BaseModel):
    employee_code: str
    pin: str = Field(pattern=r"^\d{4}$")


class AttendanceCheckInResponse(BaseModel):
    name: str
    check_in: str
    status: str

class AttendanceCheckOutResponse(BaseModel):
    name: str
    check_in: str
    check_out: str
    status: str

class TodayAttendanceItem(BaseModel):
    employee_code: str
    name: str
    check_in: str | None
    check_out: str | None
    status: str


class TodayAttendanceResponse(BaseModel):
    date: str
    employees: list[TodayAttendanceItem]
    totals: dict[str, int]