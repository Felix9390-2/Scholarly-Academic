"""
AI-powered academic insights using Groq + LLaMA 3.1.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from groq import Groq

from database import get_db
from models import Teacher, Student, Attendance, ExamScore
from auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])

GROQ_API_KEY = "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"
EXAM_ORDER = ["PT1", "PT2", "Mid Term", "PT3", "Final Exam"]
SUBJECTS_5_TO_8 = ["English","Hindi","Third Language","Mathematics","Science","Social Studies","Computer"]
SUBJECTS_9 = ["English","Third Language","Mathematics","Science","Social Studies","Computer"]

def get_subjects(c):
    return SUBJECTS_9 if c == 9 else SUBJECTS_5_TO_8


def build_student_context(student, db):
    """Build a text summary of student data for AI."""
    att = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    scores = db.query(ExamScore).filter(ExamScore.student_id == student.id).all()
    subjects = get_subjects(student.student_class)

    total_att = len(att)
    present = sum(1 for a in att if a.present)
    att_pct = round(present / total_att * 100, 1) if total_att > 0 else 0

    lines = [
        f"Student: {student.name}",
        f"Class: {student.student_class}-{student.section}",
        f"Roll Number: {student.roll_number or 'N/A'}",
        f"Attendance: {present}/{total_att} days ({att_pct}%)",
        f"Remarks from teacher: {student.remarks or 'None'}",
        "",
        "Exam Scores:"
    ]

    for exam in EXAM_ORDER:
        exam_scores = [s for s in scores if s.exam_period == exam]
        if exam_scores:
            total_obt = sum(s.marks_obtained for s in exam_scores)
            total_max = sum(s.max_marks for s in exam_scores)
            pct = round(total_obt / total_max * 100, 1) if total_max > 0 else 0
            lines.append(f"\n  {exam} (Overall: {pct}%):")
            for s in exam_scores:
                sp = round(s.marks_obtained / s.max_marks * 100, 1) if s.max_marks > 0 else 0
                lines.append(f"    {s.subject}: {s.marks_obtained}/{s.max_marks} ({sp}%)")

    # Trends
    for subj in subjects:
        vals = []
        for exam in EXAM_ORDER:
            sc = next((s for s in scores if s.subject == subj and s.exam_period == exam), None)
            if sc:
                vals.append(round(sc.marks_obtained / sc.max_marks * 100, 1) if sc.max_marks > 0 else 0)
        if len(vals) >= 2:
            if vals[-1] < vals[0] - 10:
                lines.append(f"\n⚠️ {subj} is declining: went from {vals[0]}% to {vals[-1]}%")
            elif vals[-1] > vals[0] + 10:
                lines.append(f"\n✅ {subj} is improving: went from {vals[0]}% to {vals[-1]}%")

    return "\n".join(lines)


@router.get("/summary/{student_id}")
async def ai_summary(student_id: int, user_and_role=Depends(get_current_user), db: Session = Depends(get_db)):
    user, role = user_and_role

    # Students can only view their own summary
    if role == "student":
        if user.id != student_id:
            raise HTTPException(403, "Can only view your own summary")
        student = user
    else:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(404, "Student not found")
        if user.assigned_class != student.student_class or user.assigned_section != student.section:
            raise HTTPException(403, "Not your student")

    context = build_student_context(student, db)

    client = Groq(api_key=GROQ_API_KEY)

    def generate():
        try:
            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an academic advisor AI for Scholarly, a school management app. "
                            "Analyze the student's academic data and provide a helpful, encouraging summary. "
                            "Include: 1) Overall performance summary, 2) Strengths, 3) Areas to improve, "
                            "4) Specific actionable tips, 5) Attendance feedback. "
                            "Be concise but insightful. Use emojis sparingly. "
                            "Address the student directly using 'you/your'."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this student's academic data and give improvement advice:\n\n{context}"
                    }
                ],
                temperature=0.7,
                max_tokens=800,
                stream=True,
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            yield f"\n\n⚠️ AI Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")
