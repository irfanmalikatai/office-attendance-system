from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.routers import employees, attendance, reports


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Office Attendance API",
    description="Small office attendance system",
    version="1.0.0"
)


app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"message": "Office Attendance API is running"}