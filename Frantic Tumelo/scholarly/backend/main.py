"""
Scholarly — FastAPI backend entry point.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db, SessionLocal
from models import Teacher
from auth import hash_password
from routes.auth_routes import router as auth_router
from routes.student_routes import router as student_router
from routes.attendance_routes import router as attendance_router
from routes.score_routes import router as score_router
from routes.event_routes import router as event_router
from routes.analytics_routes import router as analytics_router
from routes.admin_routes import router as admin_router
from routes.student_portal_routes import router as portal_router
from routes.ai_routes import router as ai_router

app = FastAPI(title="Scholarly API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(attendance_router)
app.include_router(score_router)
app.include_router(event_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(portal_router)
app.include_router(ai_router)

FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

if os.path.isdir(FRONTEND_DIR):
    for sub in ["css", "js"]:
        d = os.path.join(FRONTEND_DIR, sub)
        if os.path.isdir(d):
            app.mount(f"/{sub}", StaticFiles(directory=d), name=sub)

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/student.html")
async def serve_student():
    return FileResponse(os.path.join(FRONTEND_DIR, "student.html"))


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Teacher).count() > 0:
            return
        teachers = [
            {"login_name": "admin", "full_name": "Jagan Admin", "password": "admin123",
             "email": "admin@scholarly.app", "is_admin": True, "assigned_class": 7, "assigned_section": "A"},
            {"login_name": "priya", "full_name": "Priya Sharma", "password": "teacher123",
             "email": "priya@scholarly.app", "is_admin": False, "assigned_class": 8, "assigned_section": "A"},
            {"login_name": "rahul", "full_name": "Rahul Verma", "password": "teacher123",
             "email": "rahul@scholarly.app", "is_admin": False, "assigned_class": 9, "assigned_section": "A"},
        ]
        for td in teachers:
            db.add(Teacher(login_name=td["login_name"], full_name=td["full_name"],
                           hashed_password=hash_password(td["password"]), email=td["email"],
                           is_admin=td["is_admin"], assigned_class=td["assigned_class"],
                           assigned_section=td["assigned_section"]))
        db.commit()
        print("[OK] Seeded default teachers")
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()
    seed_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
