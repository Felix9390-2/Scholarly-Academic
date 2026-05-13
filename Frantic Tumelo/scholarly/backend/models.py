"""
SQLAlchemy models for Scholarly — Teacher-Driven Academic Tracker.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, Float, ForeignKey, Date
)
from sqlalchemy.orm import relationship
from database import Base


# ── Teacher (also admin) ───────────────────────────────
class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    login_name = Column(String(80), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(200), nullable=True)
    hashed_password = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    assigned_class = Column(Integer, nullable=True)
    assigned_section = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    students = relationship("Student", back_populates="teacher", lazy="select")
    events = relationship("Event", back_populates="teacher", lazy="select")

    @property
    def initials(self):
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.full_name[:2].upper()

    @property
    def class_section(self):
        if self.assigned_class and self.assigned_section:
            return f"{self.assigned_class}-{self.assigned_section}"
        return None


# ── Student (can also login) ───────────────────────────
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    login_name = Column(String(80), unique=True, nullable=True, index=True)
    hashed_password = Column(String(256), nullable=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), nullable=True)
    roll_number = Column(String(20), nullable=True)
    student_class = Column(Integer, nullable=False)
    section = Column(String(10), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    remarks = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    teacher = relationship("Teacher", back_populates="students", lazy="joined")
    attendance_records = relationship("Attendance", back_populates="student", lazy="select",
                                      cascade="all, delete-orphan")
    exam_scores = relationship("ExamScore", back_populates="student", lazy="select",
                                cascade="all, delete-orphan")

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()

    @property
    def class_section(self):
        return f"{self.student_class}-{self.section}"


# ── Attendance ─────────────────────────────────────────
class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, default=True)

    student = relationship("Student", back_populates="attendance_records")


# ── Exam Score ─────────────────────────────────────────
class ExamScore(Base):
    __tablename__ = "exam_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    exam_period = Column(String(20), nullable=False)
    subject = Column(String(50), nullable=False)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, default=100.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="exam_scores")


# ── Events (Upcoming Tests, PTM) ──────────────────────
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    event_type = Column(String(20), nullable=False)
    event_date = Column(Date, nullable=False)
    target_class = Column(Integer, nullable=True)
    target_section = Column(String(10), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    teacher = relationship("Teacher", back_populates="events")
