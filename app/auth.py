from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
import os

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "refresh_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Уменьшаем время жизни access токена
REFRESH_TOKEN_EXPIRE_DAYS = 30

ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password, hashed_password):
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def get_password_hash(password):
    return ph.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception

        login: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)
        application_submitted: bool = payload.get("application_submitted", False)
        has_pending_application: bool = payload.get("has_pending_application", False)

        if login is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.login == login).first()
    if user is None:
        raise credentials_exception
    return user


def create_token_data(user: models.User, db: Session):
    """Создает данные для токена"""
    token_data = {
        "sub": user.login,
        "is_admin": user.is_admin,
    }

    if not user.is_admin:
        token_data["application_submitted"] = user.application_submitted

        has_pending = db.query(models.Application).filter(
            models.Application.user_id == user.id,
            models.Application.status.in_(["pending", "rejected"])
        ).first() is not None

        token_data["has_pending_application"] = has_pending

    return token_data