from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import EmployeeCreate, EmployeeResponse, EmployeeUpdate


router = APIRouter(
    prefix="/employees",
    tags=["Employees"]
)


def verify_admin(x_admin_key: str | None = Header(default=None)):
    if x_admin_key != settings.admin_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin key"
        )

import bcrypt

from app.models import Employee


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=201,
    dependencies=[Depends(verify_admin)]
)
def create_employee(
    body: EmployeeCreate,
    db: Session = Depends(get_db)
):
    existing_employee = db.query(Employee).filter(
        Employee.employee_code == body.employee_code
    ).first()

    if existing_employee:
        raise HTTPException(
            status_code=409,
            detail="Employee code already exists"
        )

    pin_hash = bcrypt.hashpw(
        body.pin.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    employee = Employee(
        employee_code=body.employee_code,
        full_name=body.full_name,
        department=body.department,
        pin_hash=pin_hash,
        is_active=True
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee
@router.get(
    "",
    response_model=list[EmployeeResponse],
    dependencies=[Depends(verify_admin)]
)
def list_employees(
    db: Session = Depends(get_db)
):
    employees = db.query(Employee).all()
    return employees
@router.patch(
    "/{code}",
    response_model=EmployeeResponse,
    dependencies=[Depends(verify_admin)]
)
def update_employee(
    code: str,
    body: EmployeeUpdate,
    db: Session = Depends(get_db)
):
    employee = db.query(Employee).filter(
        Employee.employee_code == code
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    if body.full_name is not None:
        employee.full_name = body.full_name

    if body.department is not None:
        employee.department = body.department

    if body.pin is not None:
        employee.pin_hash = bcrypt.hashpw(
            body.pin.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    if body.is_active is not None:
        employee.is_active = body.is_active

    db.commit()
    db.refresh(employee)

    return employee