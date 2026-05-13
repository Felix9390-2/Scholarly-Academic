"""
Admin routes — create/manage teacher and student accounts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import Teacher, Student
from auth import require_admin, hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateTeacher(BaseModel):
    login_name: str
    full_name: str
    password: str
    email: Optional[str] = None
    assigned_class: Optional[int] = None
    assigned_section: Optional[str] = None
    is_admin: bool = False

class CreateStudent(BaseModel):
    login_name: str
    name: str
    password: str
    email: Optional[str] = None
    roll_number: Optional[str] = None
    student_class: int
    section: str


@router.get("/stats")
def admin_stats(admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "total_teachers": db.query(Teacher).count(),
        "total_students": db.query(Student).count(),
        "active_teachers": db.query(Teacher).filter(Teacher.is_active == True).count(),
        "active_students": db.query(Student).filter(Student.is_active == True).count(),
    }


@router.get("/teachers")
def list_teachers(admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    teachers = db.query(Teacher).order_by(Teacher.id).all()
    return [{
        "id": t.id, "login_name": t.login_name, "full_name": t.full_name,
        "email": t.email, "is_admin": t.is_admin, "is_active": t.is_active,
        "assigned_class": t.assigned_class, "assigned_section": t.assigned_section,
        "class_section": t.class_section, "initials": t.initials,
        "created_at": t.created_at.strftime("%b %d, %Y") if t.created_at else "—",
    } for t in teachers]


@router.post("/teachers", status_code=201)
def create_teacher(p: CreateTeacher, admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    if not p.login_name.strip() or not p.full_name.strip() or not p.password:
        raise HTTPException(400, "All fields required")
    if db.query(Teacher).filter(Teacher.login_name == p.login_name).first():
        raise HTTPException(400, "Login name already exists")
    if db.query(Student).filter(Student.login_name == p.login_name).first():
        raise HTTPException(400, "Login name already exists")
    t = Teacher(
        login_name=p.login_name.strip(), full_name=p.full_name.strip(),
        hashed_password=hash_password(p.password), email=p.email,
        assigned_class=p.assigned_class, assigned_section=p.assigned_section,
        is_admin=p.is_admin,
    )
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id, "login_name": t.login_name, "full_name": t.full_name, "message": "Teacher created"}


@router.delete("/teachers/{tid}", status_code=204)
def delete_teacher(tid: int, admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(Teacher).filter(Teacher.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    if t.id == admin.id: raise HTTPException(400, "Cannot delete yourself")
    db.delete(t); db.commit()


@router.get("/all-students")
def list_all_students(admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.student_class, Student.section, Student.name).all()
    return [{
        "id": s.id, "login_name": s.login_name, "name": s.name,
        "email": s.email, "roll_number": s.roll_number,
        "student_class": s.student_class, "section": s.section,
        "class_section": s.class_section, "initials": s.initials,
        "is_active": s.is_active,
        "teacher_name": s.teacher.full_name if s.teacher else "—",
        "created_at": s.created_at.strftime("%b %d, %Y") if s.created_at else "—",
    } for s in students]


@router.post("/students", status_code=201)
def create_student_account(p: CreateStudent, admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    if not p.login_name.strip() or not p.name.strip() or not p.password:
        raise HTTPException(400, "All fields required")
    if p.student_class < 5 or p.student_class > 9:
        raise HTTPException(400, "Class must be 5-9")
    if db.query(Teacher).filter(Teacher.login_name == p.login_name).first():
        raise HTTPException(400, "Login name already exists")
    if db.query(Student).filter(Student.login_name == p.login_name).first():
        raise HTTPException(400, "Login name already exists")
    # Find teacher for this class-section
    teacher = db.query(Teacher).filter(
        Teacher.assigned_class == p.student_class,
        Teacher.assigned_section == p.section,
    ).first()
    s = Student(
        login_name=p.login_name.strip(), name=p.name.strip(),
        hashed_password=hash_password(p.password), email=p.email,
        roll_number=p.roll_number, student_class=p.student_class,
        section=p.section, teacher_id=teacher.id if teacher else None,
    )
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "login_name": s.login_name, "name": s.name, "message": "Student created"}


@router.delete("/students/{sid}", status_code=204)
def delete_student_account(sid: int, admin: Teacher = Depends(require_admin), db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.id == sid).first()
    if not s: raise HTTPException(404, "Not found")
    db.delete(s); db.commit()
