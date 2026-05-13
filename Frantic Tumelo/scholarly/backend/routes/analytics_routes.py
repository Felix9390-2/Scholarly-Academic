"""
Analytics routes — performance trends, weakness detection, academic insights.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Teacher, Student, ExamScore, Attendance
from auth import get_current_teacher

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

EXAM_ORDER = ["PT1", "PT2", "Mid Term", "PT3", "Final Exam"]

SUBJECTS_5_TO_8 = ["English", "Hindi", "Third Language", "Mathematics", "Science", "Social Studies", "Computer"]
SUBJECTS_9 = ["English", "Third Language", "Mathematics", "Science", "Social Studies", "Computer"]

def get_subjects(cls: int):
    return SUBJECTS_9 if cls == 9 else SUBJECTS_5_TO_8


@router.get("/student/{student_id}")
def student_analytics(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.student_class != teacher.assigned_class or student.section != teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not authorized")

    scores = db.query(ExamScore).filter(ExamScore.student_id == student_id).all()
    att = db.query(Attendance).filter(Attendance.student_id == student_id).all()

    subjects = get_subjects(student.student_class)
    # Build subject-wise trend: {subject: [pct_per_exam_in_order]}
    subject_trends = {}
    exam_trends = {}
    for subj in subjects:
        subject_trends[subj] = []
        for exam in EXAM_ORDER:
            s = next((sc for sc in scores if sc.subject == subj and sc.exam_period == exam), None)
            pct = round(s.marks_obtained / s.max_marks * 100, 1) if s and s.max_marks > 0 else None
            subject_trends[subj].append(pct)

    for exam in EXAM_ORDER:
        exam_scores = [sc for sc in scores if sc.exam_period == exam]
        if exam_scores:
            total_obt = sum(sc.marks_obtained for sc in exam_scores)
            total_max = sum(sc.max_marks for sc in exam_scores)
            exam_trends[exam] = round(total_obt / total_max * 100, 1) if total_max > 0 else 0
        else:
            exam_trends[exam] = None

    # Weakness detection
    weak_subjects = []
    strong_subjects = []
    unstable_subjects = []
    declining_subjects = []

    for subj in subjects:
        vals = [v for v in subject_trends[subj] if v is not None]
        if len(vals) < 2:
            continue
        avg = sum(vals) / len(vals)
        if avg < 40:
            weak_subjects.append({"subject": subj, "avg": avg, "reason": "Consistently low"})
        elif avg >= 75:
            strong_subjects.append({"subject": subj, "avg": avg})
        
        # Check for sudden drops
        for i in range(1, len(vals)):
            if vals[i] < vals[i-1] - 20:
                declining_subjects.append({
                    "subject": subj,
                    "from_exam": EXAM_ORDER[subject_trends[subj].index(vals[i-1]) if vals[i-1] in subject_trends[subj] else 0],
                    "drop": round(vals[i-1] - vals[i], 1),
                })
                break

        # Check instability (high variance)
        if len(vals) >= 3:
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            if variance > 300:
                unstable_subjects.append({"subject": subj, "variance": round(variance, 1)})

        # No improvement check
        if len(vals) >= 3 and all(vals[i] <= vals[0] + 5 for i in range(1, len(vals))):
            if subj not in [w["subject"] for w in weak_subjects]:
                weak_subjects.append({"subject": subj, "avg": avg, "reason": "No improvement"})

    # Overall trend
    exam_vals = [exam_trends[e] for e in EXAM_ORDER if exam_trends[e] is not None]
    overall_trend = "stable"
    if len(exam_vals) >= 2:
        if exam_vals[-1] > exam_vals[0] + 5:
            overall_trend = "improving"
        elif exam_vals[-1] < exam_vals[0] - 5:
            overall_trend = "declining"

    # Attendance
    total_att = len(att)
    present_att = sum(1 for a in att if a.present)

    return {
        "student_id": student.id,
        "student_name": student.name,
        "student_class": student.student_class,
        "section": student.section,
        "subject_trends": subject_trends,
        "exam_trends": exam_trends,
        "exam_order": EXAM_ORDER,
        "subjects": subjects,
        "weak_subjects": weak_subjects,
        "strong_subjects": strong_subjects,
        "unstable_subjects": unstable_subjects,
        "declining_subjects": declining_subjects,
        "overall_trend": overall_trend,
        "attendance": {
            "total": total_att,
            "present": present_att,
            "absent": total_att - present_att,
            "percentage": round(present_att / total_att * 100, 1) if total_att > 0 else 0,
        },
    }


@router.get("/class-overview")
def class_overview(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if not teacher.assigned_class or not teacher.assigned_section:
        raise HTTPException(status_code=403, detail="Not assigned")

    students = db.query(Student).filter(
        Student.student_class == teacher.assigned_class,
        Student.section == teacher.assigned_section,
    ).all()

    subjects = get_subjects(teacher.assigned_class)
    overview = []

    for s in students:
        scores = db.query(ExamScore).filter(ExamScore.student_id == s.id).all()
        att = db.query(Attendance).filter(Attendance.student_id == s.id).all()

        total_att = len(att)
        present_att = sum(1 for a in att if a.present)

        # Latest exam percentage
        latest_exam = None
        for exam in reversed(EXAM_ORDER):
            exam_scores = [sc for sc in scores if sc.exam_period == exam]
            if exam_scores:
                total_o = sum(sc.marks_obtained for sc in exam_scores)
                total_m = sum(sc.max_marks for sc in exam_scores)
                latest_exam = {
                    "exam": exam,
                    "percentage": round(total_o / total_m * 100, 1) if total_m > 0 else 0,
                }
                break

        # Overall trend
        exam_pcts = []
        for exam in EXAM_ORDER:
            es = [sc for sc in scores if sc.exam_period == exam]
            if es:
                t_o = sum(sc.marks_obtained for sc in es)
                t_m = sum(sc.max_marks for sc in es)
                exam_pcts.append(round(t_o / t_m * 100, 1) if t_m > 0 else 0)
        trend = "stable"
        if len(exam_pcts) >= 2:
            if exam_pcts[-1] > exam_pcts[0] + 5:
                trend = "improving"
            elif exam_pcts[-1] < exam_pcts[0] - 5:
                trend = "declining"

        overview.append({
            "student_id": s.id,
            "student_name": s.name,
            "initials": s.initials,
            "roll_number": s.roll_number,
            "attendance_pct": round(present_att / total_att * 100, 1) if total_att > 0 else 0,
            "latest_exam": latest_exam,
            "overall_trend": trend,
        })

    return {
        "class": teacher.assigned_class,
        "section": teacher.assigned_section,
        "total_students": len(students),
        "students": overview,
    }
