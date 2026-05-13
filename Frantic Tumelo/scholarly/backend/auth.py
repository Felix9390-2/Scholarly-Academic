"""
JWT authentication — supports both Teacher and Student login.
"""
import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Teacher, Student

SECRET_KEY = os.getenv("SECRET_KEY", "scholarly-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Returns (user_object, role_string) — role is 'teacher' or 'student'."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        role = payload.get("role", "teacher")
        if sub is None:
            raise cred_exc
        uid = int(sub)
    except (JWTError, ValueError, TypeError):
        raise cred_exc

    if role == "student":
        user = db.query(Student).filter(Student.id == uid).first()
    else:
        user = db.query(Teacher).filter(Teacher.id == uid).first()

    if user is None:
        raise cred_exc
    return user, role


def get_current_teacher(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Teacher:
    """Dependency: must be a teacher."""
    user, role = get_current_user(token, db)
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user


def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Student:
    """Dependency: must be a student."""
    user, role = get_current_user(token, db)
    if role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return user


def require_admin(teacher: Teacher = Depends(get_current_teacher)) -> Teacher:
    if not teacher.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return teacher
