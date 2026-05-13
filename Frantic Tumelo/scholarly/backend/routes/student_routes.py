"""
Student routes — CRUD for students within teacher's assigned class-section.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import Teacher, Student
from auth import get_current_teacher

router = APIRouter(prefix="/api/students", tags=["students"])


# ── Schemas ─────────────────────────────────────────
class StudentCreate(BaseModel):
    name: str
    roll_number: Optional[str] = None
    remarks: Optional[str] = ""

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    roll_number: Optional[str] = None
    remarks: Optional[str] = None

class StudentOut(BaseModel):
    id: int
    name: str
    roll_number: str | None
    student_class: int
    section: str
    class_section: str
    remarks: str
    initials: str
    created_at: str

    class Config:
        from_attributes = True


def _check_assignment(teacher: Teacher):
    """Ensure teacher is assigned to a class-section."""
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to any class-section."
        )


# ── List students ──────────────────────────────────
@router.get("/", response_model=list[StudentOut])
def list_students(
    search: str = Query("", description="Search by name or roll number"),
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    _check_assignment(teacher)
    q = db.query(Student).filter(
        Student.student_class == teacher.assigned_class,
        Student.section == teacher.assigned_section,
    )
    if search:
        q = q.filter(
            Student.name.ilike(f"%{search}%")
            | Student.roll_number.ilike(f"%{search}%")
        )
    students = q.order_by(Student.name).all()
    return [
        StudentOut(
            id=s.id, name=s.name, roll_number=s.roll_number,
            student_class=s.student_class, section=s.section,
            class_section=s.class_section, remarks=s.remarks or "",
            initials=s.initials,
            created_at=s.created_at.strftime("%b %d, %Y") if s.created_at else "—",
        )
        for s in students
    ]


# ── Get single student ────────────────────────────
@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    _check_assignment(teacher)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not authorized for this student")
    return StudentOut(
        id=student.id, name=student.name, roll_number=student.roll_number,
        student_class=student.student_class, section=student.section,
        class_section=student.class_section, remarks=student.remarks or "",
        initials=student.initials,
        created_at=student.created_at.strftime("%b %d, %Y") if student.created_at else "—",
    )


# ── Create student ────────────────────────────────
@router.post("/", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    _check_assignment(teacher)
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Student name is required")

    student = Student(
        name=payload.name.strip(),
        roll_number=payload.roll_number,
        student_class=teacher.assigned_class,
        section=teacher.assigned_section,
        teacher_id=teacher.id,
        remarks=payload.remarks or "",
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentOut(
        id=student.id, name=student.name, roll_number=student.roll_number,
        student_class=student.student_class, section=student.section,
        class_section=student.class_section, remarks=student.remarks or "",
        initials=student.initials,
        created_at=student.created_at.strftime("%b %d, %Y") if student.created_at else "—",
    )


# ── Update student ────────────────────────────────
@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    _check_assignment(teacher)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not authorized for this student")

    if payload.name is not None:
        student.name = payload.name.strip()
    if payload.roll_number is not None:
        student.roll_number = payload.roll_number
    if payload.remarks is not None:
        student.remarks = payload.remarks

    db.commit()
    db.refresh(student)
    return StudentOut(
        id=student.id, name=student.name, roll_number=student.roll_number,
        student_class=student.student_class, section=student.section,
        class_section=student.class_section, remarks=student.remarks or "",
        initials=student.initials,
        created_at=student.created_at.strftime("%b %d, %Y") if student.created_at else "—",
    )


# ── Delete student ────────────────────────────────
@router.delete("/{student_id}", status_code=204)
def delete_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    _check_assignment(teacher)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not authorized for this student")
    db.delete(student)
    db.commit()
