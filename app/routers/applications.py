from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.utils.sensor_utils import (
    process_application_rooms
)

router = APIRouter(prefix="/applications", tags=["Applications"])

# ---------- Справочники ----------
@router.get("/dictionaries", response_model=schemas.DictionariesResponse)
def get_dictionaries():
    """Получить справочники комнат и датчиков"""
    return {
        "rooms": models.ROOM_TYPES,
        "sensors": models.SENSOR_TYPES
    }

# ---------- Для пользователей ----------
@router.post("/", response_model=schemas.ApplicationResponse)
def create_application(
        application_data: schemas.ApplicationCreate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    print('─' * 50)
    print('СОЗДАНИЕ ЗАЯВКИ')
    print('─' * 50)
    print(application_data.rooms_config)
    print('─' * 50)

    """Создать новую заявку"""
    # Проверка прав
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot create applications"
        )

    # Валидация всех комнат и датчиков
    for room_config in application_data.rooms_config:
        # Проверяем существование комнаты в словаре по типу
        if room_config.room_type not in models.ROOM_TYPES.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid room type: {room_config.room_type}"
            )

        # Проверяем все датчики в комнате
        for sensor_id in room_config.sensor_ids:
            if sensor_id not in models.SENSOR_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sensor ID: {sensor_id} in room {room_config.room_type}"
                )

    # Дополнительная валидация: проверяем, что нет пустых комнат без датчиков
    empty_rooms = [rc for rc in application_data.rooms_config if not rc.sensor_ids]
    if empty_rooms:
        room_types = [rc.room_type for rc in empty_rooms]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rooms must have at least one sensor: {room_types}"
        )

    # Создаем заявку с новой структурой
    application = models.Application(
        user_id=current_user.id,
        rooms_config=[rc.dict() for rc in application_data.rooms_config],  # Конвертируем в dict для JSON
        status="pending"
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    # Формируем ответ
    return {
        "id": application.id,
        "user_id": application.user_id,
        "rooms_config": application.rooms_config,
        "status": application.status,
        "rejection_comment": application.rejection_comment,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "user_login": current_user.login
    }

@router.get("/my", response_model=list[schemas.ApplicationResponse])
def get_my_applications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить мои заявки"""
    applications = db.query(models.Application).filter(
        models.Application.user_id == current_user.id
    ).order_by(models.Application.created_at.desc()).all()

    return [
        {
            "id": app.id,
            "user_id": app.user_id,
            "rooms_config": app.rooms_config,
            "status": app.status,
            "rejection_comment": app.rejection_comment,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "user_login": current_user.login
        }
        for app in applications
    ]

# ---------- Для админов ----------
@router.get("/admin/all", response_model=list[schemas.ApplicationResponse])
def get_all_applications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все заявки (только для админа)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    applications = db.query(models.Application).join(models.User).order_by(
        models.Application.created_at.desc()
    ).all()

    return [
        {
            "id": app.id,
            "user_id": app.user_id,
            "rooms_config": app.rooms_config,
            "status": app.status,
            "rejection_comment": app.rejection_comment,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "user_login": app.user.login
        }
        for app in applications
    ]


@router.get("/admin/pending", response_model=list[schemas.ApplicationResponse])
def get_pending_applications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить заявки в ожидании (только для админа)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    applications = db.query(models.Application).join(models.User).filter(
        models.Application.status == "pending"
    ).order_by(models.Application.created_at.desc()).all()

    return [
        {
            **app.__dict__,
            "user_login": app.user.login
        }
        for app in applications
    ]

@router.get("/admin/{user_id}/applications", response_model=list[schemas.ApplicationResponse])
def get_user_applications(
        user_id: int,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Получить все заявки пользователя (только для админа)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Проверяем, существует ли пользователь
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    applications = db.query(models.Application).filter(
        models.Application.user_id == user_id
    ).order_by(models.Application.created_at.desc()).all()

    return [
        {
            "id": app.id,
            "user_id": app.user_id,
            "rooms_config": app.rooms_config,
            "status": app.status,
            "rejection_comment": app.rejection_comment,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "user_login": user.login
        }
        for app in applications
    ]

@router.get("/{application_id}", response_model=schemas.ApplicationResponse)
def get_application(
    application_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить заявку по ID"""
    application = db.query(models.Application).join(models.User).filter(
        models.Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Проверяем права доступа
    if not current_user.is_admin and application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return {
        "id": application.id,
        "user_id": application.user_id,
        "rooms_config": application.rooms_config,
        "status": application.status,
        "rejection_comment": application.rejection_comment,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "user_login": application.user.login
    }


@router.put("/{application_id}")
def update_application_status(
        application_id: int,
        status_data: schemas.ApplicationUpdate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Обновить статус заявки (только для админа)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    application = db.query(models.Application).filter(
        models.Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    if status_data.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved' or 'rejected'"
        )

    try:
        # Обновляем статус и комментарий
        application.status = status_data.status
        application.rejection_comment = status_data.rejection_comment if status_data.status == "rejected" else None

        if status_data.status == "approved":
            # ОДОБРЕНИЕ: application_submitted = true
            user = db.query(models.User).filter(
                models.User.id == application.user_id
            ).first()

            if not user:
                raise Exception("User not found")

            user.application_submitted = True

            if not application.rooms_config:
                raise Exception("Application has no rooms_config")
            # Используем новую утилиту для обработки всех комнат
            created_room_ids = process_application_rooms(
                db=db,
                user_id=application.user_id,
                rooms_config=application.rooms_config
            )

            application.created_room_ids = created_room_ids

        db.commit()
        db.refresh(application)

    # except Exception as e:
    #     db.rollback()
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail=f"Error updating application: {str(e)}"
    #     )

    except Exception as e:
        db.rollback()
        print("ERROR:", repr(e))
        raise

    return {
        "message": f"Application {status_data.status} successfully",
        "rejection_comment": application.rejection_comment
    }