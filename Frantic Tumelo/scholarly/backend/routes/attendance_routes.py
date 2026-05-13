"""
Attendance routes — manual entry by teachers for their class students.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from database import get_db
from models import Teacher, Student, Attendance
from auth import get_current_teacher

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


# ── Schemas ─────────────────────────────────────────
class AttendanceEntry(BaseModel):
    student_id: int
    date: date
    present: bool

class BulkAttendanceEntry(BaseModel):
    date: date
    records: list[dict]  # [{"student_id": 1, "present": true}, ...]

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    date: str
    present: bool

    class Config:
        from_attributes = True

class AttendanceSummary(BaseModel):
    student_id: int
    student_name: str
    total_days: int
    present_days: int
    absent_days: int
    percentage: float


def _verify_student_access(teacher: Teacher, student: Student):
    """Ensure teacher has access to this student's class-section."""
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not assigned to any class")
    if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not authorized for this student")


# ── Record single attendance ──────────────────────
@router.post("/", response_model=AttendanceOut, status_code=201)
def record_attendance(
    payload: AttendanceEntry,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _verify_student_access(teacher, student)

    # Check if attendance already exists for this date
    existing = db.query(Attendance).filter(
        Attendance.student_id == payload.student_id,
        Attendance.date == payload.date,
    ).first()

    if existing:
        existing.present = payload.present
        db.commit()
        db.refresh(existing)
        return AttendanceOut(
            id=existing.id, student_id=existing.student_id,
            student_name=student.name, date=str(existing.date),
            present=existing.present,
        )

    att = Attendance(
        student_id=payload.student_id,
        date=payload.date,
        present=payload.present,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return AttendanceOut(
        id=att.id, student_id=att.student_id,
        student_name=student.name, date=str(att.date),
        present=att.present,
    )


# ── Bulk attendance for a date ────────────────────
@router.post("/bulk", status_code=201)
def bulk_attendance(
    payload: BulkAttendanceEntry,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not assigned to any class")

    results = []
    for record in payload.records:
        student_id = record.get("student_id")
        present = record.get("present", True)

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            continue
        if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
            continue

        existing = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.date == payload.date,
        ).first()

        if existing:
            existing.present = present
        else:
            att = Attendance(student_id=student_id, date=payload.date, present=present)
            db.add(att)

        results.append({"student_id": student_id, "present": present})

    db.commit()
    return {"message": f"Attendance recorded for {len(results)} students", "count": len(results)}


# ── Get attendance for a specific date ────────────
@router.get("/date/{att_date}")
def get_attendance_by_date(
    att_date: date,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not assigned to any class")

    students = db.query(Student).filter(
        Student.student_class == teacher.assigned_class,
        Student.section == teacher.assigned_section,
    ).order_by(Student.name).all()

    attendance_map = {}
    records = db.query(Attendance).filter(
        Attendance.date == att_date,
        Attendance.student_id.in_([s.id for s in students])
    ).all()
    for r in records:
        attendance_map[r.student_id] = r.present

    result = []
    for s in students:
        result.append({
            "student_id": s.id,
            "student_name": s.name,
            "roll_number": s.roll_number,
            "present": attendance_map.get(s.id, None),  # None = not recorded
        })
    return result


# ── Attendance summary for all students ───────────
@router.get("/summary", response_model=list[AttendanceSummary])
def attendance_summary(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not assigned to any class")

    students = db.query(Student).filter(
        Student.student_class == teacher.assigned_class,
        Student.section == teacher.assigned_section,
    ).order_by(Student.name).all()

    summaries = []
    for s in students:
        records = db.query(Attendance).filter(Attendance.student_id == s.id).all()
        total = len(records)
        present = sum(1 for r in records if r.present)
        absent = total - present
        pct = round((present / total * 100), 1) if total > 0 else 0.0
        summaries.append(AttendanceSummary(
            student_id=s.id, student_name=s.name,
            total_days=total, present_days=present,
            absent_days=absent, percentage=pct,
        ))
    return summaries


# ── Single student attendance history ─────────────
@router.get("/student/{student_id}")
def student_attendance(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _verify_student_access(teacher, student)

    records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(Attendance.date.desc()).all()

    total = len(records)
    present = sum(1 for r in records if r.present)

    return {
        "student_id": student.id,
        "student_name": student.name,
        "total_days": total,
        "present_days": present,
        "absent_days": total - present,
        "percentage": round((present / total * 100), 1) if total > 0 else 0.0,
        "records": [
            {"date": str(r.date), "present": r.present} for r in records
        ]
    }
