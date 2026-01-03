# users.py или добавить в существующий роутер
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


# ---------- Для админов ----------
@router.get("/admin/list", response_model=List[schemas.UserListResponse])
def get_all_users(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Получить всех пользователей (только для админа)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Получаем пользователей с количеством заявок
    users = db.query(
        models.User,
        func.count(models.Application.id).label('applications_count')
    ).outerjoin(
        models.Application, models.User.id == models.Application.user_id
    ).group_by(models.User.id).order_by(models.User.id).all()

    result = []
    for user, app_count in users:
        # Получаем количество заявок по статусам
        pending_count = db.query(func.count(models.Application.id)).filter(
            models.Application.user_id == user.id,
            models.Application.status == "pending"
        ).scalar() or 0

        approved_count = db.query(func.count(models.Application.id)).filter(
            models.Application.user_id == user.id,
            models.Application.status == "approved"
        ).scalar() or 0

        rejected_count = db.query(func.count(models.Application.id)).filter(
            models.Application.user_id == user.id,
            models.Application.status == "rejected"
        ).scalar() or 0

        result.append({
            "id": user.id,
            "login": user.login,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "application_submitted": user.application_submitted,
            "applications_count": app_count,
            "pending_applications": pending_count,
            "approved_applications": approved_count,
            "rejected_applications": rejected_count,
            "created_at": user.created_at if hasattr(user, 'created_at') else None
        })

    return result


