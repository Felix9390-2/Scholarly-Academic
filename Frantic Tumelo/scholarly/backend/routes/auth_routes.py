"""
Auth routes — login (teacher or student) and profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Teacher, Student
from auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try teacher first
    teacher = db.query(Teacher).filter(Teacher.login_name == form.username).first()
    if teacher and verify_password(form.password, teacher.hashed_password):
        if not teacher.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        token = create_access_token({"sub": str(teacher.id), "role": "teacher"})
        return TokenResponse(access_token=token, role="teacher")

    # Try student
    student = db.query(Student).filter(Student.login_name == form.username).first()
    if student and student.hashed_password and verify_password(form.password, student.hashed_password):
        if not student.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        token = create_access_token({"sub": str(student.id), "role": "student"})
        return TokenResponse(access_token=token, role="student")

    raise HTTPException(status_code=401, detail="Invalid login name or password")


@router.get("/me")
def me(user_and_role=Depends(get_current_user)):
    user, role = user_and_role
    if role == "teacher":
        return {
            "id": user.id, "login_name": user.login_name,
            "full_name": user.full_name, "email": user.email or "",
            "is_admin": user.is_admin, "is_active": user.is_active,
            "assigned_class": user.assigned_class,
            "assigned_section": user.assigned_section,
            "class_section": user.class_section,
            "initials": user.initials,
            "role": "teacher",
            "created_at": user.created_at.strftime("%b %d, %Y") if user.created_at else "—",
        }
    else:
        return {
            "id": user.id, "login_name": user.login_name,
            "full_name": user.name, "email": user.email or "",
            "is_admin": False, "is_active": user.is_active,
            "assigned_class": user.student_class,
            "assigned_section": user.section,
            "class_section": user.class_section,
            "initials": user.initials,
            "role": "student",
            "roll_number": user.roll_number,
            "remarks": user.remarks or "",
            "created_at": user.created_at.strftime("%b %d, %Y") if user.created_at else "—",
        }
