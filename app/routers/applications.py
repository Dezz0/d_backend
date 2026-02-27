from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.utils.sensor_utils import create_room_from_application, create_sensor_from_application

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
    """Создать новую заявку"""
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot create applications"
        )

    # Валидация комнат
    for room_id in application_data.rooms:
        if room_id not in models.ROOM_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid room ID: {room_id}"
            )

    # Валидация датчиков
    for room_id, sensor_ids in application_data.sensors.items():
        if room_id not in application_data.rooms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id} not in selected rooms"
            )
        for sensor_id in sensor_ids:
            if sensor_id not in models.SENSOR_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sensor ID: {sensor_id}"
                )

    # Создаем заявку
    application = models.Application(
        user_id=current_user.id,
        rooms=application_data.rooms,
        sensors=application_data.sensors,
        status="pending"
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        **application.__dict__,
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
            "rooms": app.rooms,
            "sensors": app.sensors,
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
            "rooms": app.rooms,
            "sensors": app.sensors,
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
            "rooms": app.rooms,
            "sensors": app.sensors,
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
        "rooms": application.rooms,
        "sensors": application.sensors,
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
            user = db.query(models.User).filter(models.User.id == application.user_id).first()
            user.application_submitted = True

            created_room_ids = []

            for room_id in application.rooms:
                try:
                    # создаем комнату
                    room = create_room_from_application(db, room_id)
                    created_room_ids.append(room.id)

                    # получаем датчики
                    sensor_ids = []
                    if isinstance(application.sensors, dict):
                        room_key = str(room_id)
                        if room_key in application.sensors:
                            sensor_ids = application.sensors[room_key]
                        elif room_id in application.sensors:
                            sensor_ids = application.sensors[room_id]

                    # создаем датчики
                    for idx, sensor_type_id in enumerate(sensor_ids, start=1):
                        sensor_type_name = models.SENSOR_TYPES.get(sensor_type_id)
                        if not sensor_type_name:
                            continue

                        sensor_type_map = {
                            "Датчик температуры": "temperature",
                            "Датчик освещения": "light",
                            "Датчик газа": "gas",
                            "Датчик влажности": "humidity",
                            "Датчик вентиляции": "ventilation",
                        }

                        sensor_type_key = sensor_type_map.get(sensor_type_name)
                        if sensor_type_key:
                            try:
                                create_sensor_from_application(db, sensor_type_key, idx, room.id)
                            except Exception as e:
                                print(f"Error creating sensor {sensor_type_key} in room {room.id}: {e}")
                                continue

                except Exception as e:
                    print(f"Error creating room {room_id}: {e}")
                    continue

            application.created_room_ids = created_room_ids

        db.commit()
        db.refresh(application)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating application: {str(e)}"
        )

    return {
        "message": f"Application {status_data.status} successfully",
        "rejection_comment": application.rejection_comment
    }