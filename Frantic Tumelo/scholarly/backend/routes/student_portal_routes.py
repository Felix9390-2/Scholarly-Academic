"""
Student-facing routes — read-only access to own data.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Student, Attendance, ExamScore, Event
from auth import get_current_student

router = APIRouter(prefix="/api/my", tags=["student-portal"])

EXAM_ORDER = ["PT1", "PT2", "Mid Term", "PT3", "Final Exam"]
SUBJECTS_5_TO_8 = ["English","Hindi","Third Language","Mathematics","Science","Social Studies","Computer"]
SUBJECTS_9 = ["English","Third Language","Mathematics","Science","Social Studies","Computer"]

def get_subjects(c):
    return SUBJECTS_9 if c == 9 else SUBJECTS_5_TO_8


@router.get("/attendance")
def my_attendance(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    records = db.query(Attendance).filter(Attendance.student_id == student.id).order_by(Attendance.date.desc()).all()
    total = len(records)
    present = sum(1 for r in records if r.present)
    return {
        "total_days": total, "present_days": present, "absent_days": total - present,
        "percentage": round(present / total * 100, 1) if total > 0 else 0,
        "records": [{"date": str(r.date), "present": r.present} for r in records],
    }


@router.get("/scores")
def my_scores(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    scores = db.query(ExamScore).filter(ExamScore.student_id == student.id).all()
    by_exam = {}
    for s in scores:
        by_exam.setdefault(s.exam_period, []).append({
            "subject": s.subject, "marks_obtained": s.marks_obtained,
            "max_marks": s.max_marks,
            "percentage": round(s.marks_obtained / s.max_marks * 100, 1) if s.max_marks > 0 else 0,
        })
    summaries = {}
    for exam, subjects in by_exam.items():
        to = sum(s["marks_obtained"] for s in subjects)
        tm = sum(s["max_marks"] for s in subjects)
        summaries[exam] = {"subjects": subjects, "total_obtained": to, "total_max": tm,
                           "percentage": round(to / tm * 100, 1) if tm > 0 else 0}
    return {"scores_by_exam": summaries, "exam_periods": EXAM_ORDER,
            "subjects": get_subjects(student.student_class)}


@router.get("/analytics")
def my_analytics(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    scores = db.query(ExamScore).filter(ExamScore.student_id == student.id).all()
    att = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    subjects = get_subjects(student.student_class)

    subject_trends = {}
    exam_trends = {}
    for subj in subjects:
        subject_trends[subj] = []
        for exam in EXAM_ORDER:
            s = next((sc for sc in scores if sc.subject == subj and sc.exam_period == exam), None)
            subject_trends[subj].append(round(s.marks_obtained / s.max_marks * 100, 1) if s and s.max_marks > 0 else None)

    for exam in EXAM_ORDER:
        es = [sc for sc in scores if sc.exam_period == exam]
        if es:
            exam_trends[exam] = round(sum(sc.marks_obtained for sc in es) / sum(sc.max_marks for sc in es) * 100, 1)
        else:
            exam_trends[exam] = None

    # Weakness detection
    weak, strong = [], []
    for subj in subjects:
        vals = [v for v in subject_trends[subj] if v is not None]
        if len(vals) < 1: continue
        avg = sum(vals) / len(vals)
        if avg < 40: weak.append({"subject": subj, "avg": avg, "reason": "Consistently low"})
        elif avg >= 75: strong.append({"subject": subj, "avg": avg})

    exam_vals = [exam_trends[e] for e in EXAM_ORDER if exam_trends[e] is not None]
    trend = "stable"
    if len(exam_vals) >= 2:
        if exam_vals[-1] > exam_vals[0] + 5: trend = "improving"
        elif exam_vals[-1] < exam_vals[0] - 5: trend = "declining"

    total_att = len(att)
    present_att = sum(1 for a in att if a.present)

    return {
        "student_name": student.name, "student_class": student.student_class,
        "section": student.section, "remarks": student.remarks or "",
        "subject_trends": subject_trends, "exam_trends": exam_trends,
        "exam_order": EXAM_ORDER, "subjects": subjects,
        "weak_subjects": weak, "strong_subjects": strong,
        "overall_trend": trend,
        "attendance": {
            "total": total_att, "present": present_att,
            "absent": total_att - present_att,
            "percentage": round(present_att / total_att * 100, 1) if total_att > 0 else 0,
        },
    }


@router.get("/events")
def my_events(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    events = db.query(Event).filter(
        (Event.target_class == student.student_class) | (Event.target_class == None),
        (Event.target_section == student.section) | (Event.target_section == None),
    ).order_by(Event.event_date).all()
    return [{
        "id": e.id, "title": e.title, "description": e.description or "",
        "event_type": e.event_type, "event_date": str(e.event_date),
        "target_class": e.target_class, "target_section": e.target_section,
    } for e in events]
