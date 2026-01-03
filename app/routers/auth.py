from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_current_user,
    create_token_data
)
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.login == user_data.login).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login already exists"
        )

    new_user = models.User(
        login=user_data.login,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        middle_name=user_data.middle_name,
        is_admin=False,
        application_submitted=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "login": new_user.login,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "middle_name": new_user.middle_name,
        "is_active": new_user.is_active,
        "is_admin": new_user.is_admin,
        "application_submitted": new_user.application_submitted,
        "has_pending_application": False
    }

@router.post("/login", response_model=schemas.TokenPair)
def login(data: schemas.UserAuth, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.login == data.login).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token_data = create_token_data(user, db)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=schemas.TokenPair)
def refresh_token(refresh_data: schemas.RefreshToken, db: Session = Depends(get_db)):
    payload = verify_refresh_token(refresh_data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    login = payload.get("sub")
    user = db.query(models.User).filter(models.User.login == login).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    token_data = create_token_data(user, db)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)  # Выдаем новый refresh токен

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/change_password")
def change_password(
    data: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password successfully changed"}


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Получаем информацию о pending заявках
    has_pending = db.query(models.Application).filter(
        models.Application.user_id == current_user.id,
        models.Application.status.in_(["pending", "rejected"])
    ).first() is not None

    # Возвращаем словарь с добавленным полем
    return {
        "id": current_user.id,
        "login": current_user.login,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "middle_name": current_user.middle_name,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "application_submitted": current_user.application_submitted,
        "has_pending_application": has_pending
    }


@router.get("/profile", response_model=schemas.UserProfileResponse)
def get_user_profile(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Получить профиль пользователя со статистикой"""
    # Статистика по заявкам
    total_applications = db.query(func.count(models.Application.id)).filter(
        models.Application.user_id == current_user.id
    ).scalar() or 0

    pending_applications = db.query(func.count(models.Application.id)).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "pending"
    ).scalar() or 0

    approved_applications = db.query(func.count(models.Application.id)).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "approved"
    ).scalar() or 0

    rejected_applications = db.query(func.count(models.Application.id)).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "rejected"
    ).scalar() or 0

    # Статистика по комнатам и датчикам (только для одобренных заявок)
    approved_application = db.query(models.Application).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "approved"
    ).first()

    total_rooms = 0
    total_sensors = 0

    if approved_application:
        total_rooms = len(approved_application.rooms)
        total_sensors = sum(len(sensors) for sensors in approved_application.sensors.values())

    # Получаем pending заявки для has_pending_application
    has_pending = db.query(models.Application).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "pending"
    ).first() is not None

    return {
        "id": current_user.id,
        "login": current_user.login,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "middle_name": current_user.middle_name,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "application_submitted": current_user.application_submitted,
        "has_pending_application": has_pending,
        "created_at": current_user.created_at,
        "total_applications": total_applications,
        "pending_applications": pending_applications,
        "approved_applications": approved_applications,
        "rejected_applications": rejected_applications,
        "total_rooms": total_rooms,
        "total_sensors": total_sensors
    }


@router.put("/profile", response_model=schemas.UserProfileResponse)
def update_user_profile(
        user_data: schemas.UserUpdate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Обновить профиль пользователя (ФИО)"""
    # Обновляем только предоставленные поля
    if user_data.first_name is not None:
        current_user.first_name = user_data.first_name
    if user_data.last_name is not None:
        current_user.last_name = user_data.last_name
    if user_data.middle_name is not None:
        current_user.middle_name = user_data.middle_name

    db.commit()
    db.refresh(current_user)

    # Возвращаем обновленный профиль со статистикой
    return get_user_profile(current_user=current_user, db=db)