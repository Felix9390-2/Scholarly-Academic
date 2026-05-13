"""
Exam score routes — marks entry by exam period and subject.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Teacher, Student, ExamScore
from auth import get_current_teacher

router = APIRouter(prefix="/api/scores", tags=["scores"])

SUBJECTS_5_TO_8 = ["English","Hindi","Third Language","Mathematics","Science","Social Studies","Computer"]
SUBJECTS_9 = ["English","Third Language","Mathematics","Science","Social Studies","Computer"]
EXAM_PERIODS = ["PT1","PT2","Mid Term","PT3","Final Exam"]

def get_subjects_for_class(c):
    return SUBJECTS_9 if c == 9 else SUBJECTS_5_TO_8

class ScoreEntry(BaseModel):
    student_id: int
    exam_period: str
    subject: str
    marks_obtained: float
    max_marks: float = 100.0

class BulkScoreEntry(BaseModel):
    student_id: int
    exam_period: str
    scores: list[dict]

class ScoreOut(BaseModel):
    id: int
    student_id: int
    exam_period: str
    subject: str
    marks_obtained: float
    max_marks: float
    percentage: float
    class Config:
        from_attributes = True

def _verify(t, s):
    if not t.assigned_class or not t.assigned_section:
        raise HTTPException(403, "Not assigned")
    if s.student_class != t.assigned_class or s.section != t.assigned_section:
        raise HTTPException(403, "Not authorized")

@router.get("/config")
def get_config(teacher: Teacher = Depends(get_current_teacher)):
    c = teacher.assigned_class or 5
    return {"subjects": get_subjects_for_class(c), "exam_periods": EXAM_PERIODS}

@router.post("/", response_model=ScoreOut, status_code=201)
def enter_score(payload: ScoreEntry, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student: raise HTTPException(404, "Student not found")
    _verify(teacher, student)
    if payload.subject not in get_subjects_for_class(student.student_class):
        raise HTTPException(400, "Invalid subject")
    if payload.exam_period not in EXAM_PERIODS:
        raise HTTPException(400, "Invalid exam period")
    if payload.marks_obtained < 0 or payload.marks_obtained > payload.max_marks:
        raise HTTPException(400, "Invalid marks")
    existing = db.query(ExamScore).filter(ExamScore.student_id == payload.student_id, ExamScore.exam_period == payload.exam_period, ExamScore.subject == payload.subject).first()
    if existing:
        existing.marks_obtained = payload.marks_obtained
        existing.max_marks = payload.max_marks
        db.commit(); db.refresh(existing)
        return ScoreOut(id=existing.id, student_id=existing.student_id, exam_period=existing.exam_period, subject=existing.subject, marks_obtained=existing.marks_obtained, max_marks=existing.max_marks, percentage=round(existing.marks_obtained/existing.max_marks*100,1))
    score = ExamScore(student_id=payload.student_id, exam_period=payload.exam_period, subject=payload.subject, marks_obtained=payload.marks_obtained, max_marks=payload.max_marks)
    db.add(score); db.commit(); db.refresh(score)
    return ScoreOut(id=score.id, student_id=score.student_id, exam_period=score.exam_period, subject=score.subject, marks_obtained=score.marks_obtained, max_marks=score.max_marks, percentage=round(score.marks_obtained/score.max_marks*100,1))

@router.post("/bulk", status_code=201)
def bulk_score_entry(payload: BulkScoreEntry, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student: raise HTTPException(404, "Student not found")
    _verify(teacher, student)
    if payload.exam_period not in EXAM_PERIODS:
        raise HTTPException(400, "Invalid exam period")
    valid = get_subjects_for_class(student.student_class)
    count = 0
    for entry in payload.scores:
        subj = entry.get("subject"); marks = entry.get("marks_obtained",0); mx = entry.get("max_marks",100)
        if subj not in valid or marks < 0 or marks > mx: continue
        ex = db.query(ExamScore).filter(ExamScore.student_id==payload.student_id, ExamScore.exam_period==payload.exam_period, ExamScore.subject==subj).first()
        if ex: ex.marks_obtained=marks; ex.max_marks=mx
        else: db.add(ExamScore(student_id=payload.student_id, exam_period=payload.exam_period, subject=subj, marks_obtained=marks, max_marks=mx))
        count += 1
    db.commit()
    return {"message": f"Scores entered for {count} subjects", "count": count}

@router.get("/student/{student_id}")
def get_student_scores(student_id: int, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student: raise HTTPException(404, "Student not found")
    _verify(teacher, student)
    scores = db.query(ExamScore).filter(ExamScore.student_id == student_id).order_by(ExamScore.exam_period, ExamScore.subject).all()
    by_exam = {}
    for s in scores:
        by_exam.setdefault(s.exam_period, []).append({"id":s.id,"subject":s.subject,"marks_obtained":s.marks_obtained,"max_marks":s.max_marks,"percentage":round(s.marks_obtained/s.max_marks*100,1) if s.max_marks>0 else 0})
    exam_summaries = {}
    for exam, subjects in by_exam.items():
        to = sum(s["marks_obtained"] for s in subjects); tm = sum(s["max_marks"] for s in subjects)
        exam_summaries[exam] = {"subjects":subjects,"total_obtained":to,"total_max":tm,"percentage":round(to/tm*100,1) if tm>0 else 0}
    return {"student_id":student.id,"student_name":student.name,"student_class":student.student_class,"section":student.section,"valid_subjects":get_subjects_for_class(student.student_class),"exam_periods":EXAM_PERIODS,"scores_by_exam":exam_summaries}

@router.get("/exam/{exam_period}")
def get_exam_scores(exam_period: str, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    if not teacher.assigned_class: raise HTTPException(403, "Not assigned")
    students = db.query(Student).filter(Student.student_class==teacher.assigned_class, Student.section==teacher.assigned_section).order_by(Student.name).all()
    result = []
    for s in students:
        sc = db.query(ExamScore).filter(ExamScore.student_id==s.id, ExamScore.exam_period==exam_period).all()
        ss = {x.subject:{"marks_obtained":x.marks_obtained,"max_marks":x.max_marks,"percentage":round(x.marks_obtained/x.max_marks*100,1) if x.max_marks>0 else 0} for x in sc}
        to=sum(x.marks_obtained for x in sc); tm=sum(x.max_marks for x in sc)
        result.append({"student_id":s.id,"student_name":s.name,"roll_number":s.roll_number,"subjects":ss,"total_obtained":to,"total_max":tm,"percentage":round(to/tm*100,1) if tm>0 else 0})
    return result
