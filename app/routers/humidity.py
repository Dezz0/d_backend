from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from typing import List

router = APIRouter(prefix="/sensors/humidity", tags=["Humidity"])

@router.post("/", response_model=schemas.HumiditySensorResponse)
def add_humidity_data(
    data: schemas.HumiditySensorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавить/обновить данные датчика влажности"""
    # Проверяем, что комната существует (должна быть создана через заявку)
    room = db.query(models.Room).filter(models.Room.name == data.room_name).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room '{data.room_name}' not found. Room must be created through application first."
        )

    # Проверяем, существует ли датчик
    sensor = db.query(models.HumiditySensor).filter(
        models.HumiditySensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        # Обновляем существующий датчик
        if sensor.room_id != room.id:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor exists in different room: {sensor.room.name}"
            )
        sensor.humidity_level = data.humidity_level
    else:
        # Создаем новый датчик (только если комната существует)
        sensor = models.HumiditySensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            humidity_level=data.humidity_level
        )
        db.add(sensor)

    db.commit()
    db.refresh(sensor)

    return {
        "sensor_id": sensor.sensor_id,
        "room_name": room.name,
        "humidity_level": sensor.humidity_level
    }

@router.get("/list", response_model=List[schemas.HumiditySensorResponse])
def get_all_humidity_sensors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики влажности в доме"""
    sensors = db.query(models.HumiditySensor).all()
    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": sensor.room.name,
            "humidity_level": sensor.humidity_level
        }
        for sensor in sensors
    ]

@router.get("/room/{room_id}", response_model=List[schemas.HumiditySensorResponse])
def get_room_humidity_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить датчики влажности в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors = db.query(models.HumiditySensor).filter(
        models.HumiditySensor.room_id == room_id
    ).all()

    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": room.name,
            "humidity_level": sensor.humidity_level
        }
        for sensor in sensors
    ]