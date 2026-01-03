from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from typing import List

router = APIRouter(prefix="/sensors/temperature", tags=["Temperature"])

@router.post("/", response_model=schemas.TemperatureSensorResponse)
def add_temperature_data(
    data: schemas.TemperatureSensorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавить/обновить данные датчика температуры"""
    # Проверяем, что комната существует (должна быть создана через заявку)
    room = db.query(models.Room).filter(models.Room.name == data.room_name).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room '{data.room_name}' not found. Room must be created through application first."
        )

    # Проверяем, существует ли датчик
    sensor = db.query(models.TemperatureSensor).filter(
        models.TemperatureSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        # Обновляем существующий датчик
        if sensor.room_id != room.id:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor exists in different room: {sensor.room.name}"
            )
        sensor.value = data.value
    else:
        # Создаем новый датчик (только если комната существует)
        sensor = models.TemperatureSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            value=data.value
        )
        db.add(sensor)

    db.commit()
    db.refresh(sensor)

    return {
        "sensor_id": sensor.sensor_id,
        "room_name": room.name,
        "value": sensor.value
    }

@router.get("/list", response_model=List[schemas.TemperatureSensorResponse])
def get_all_temperature_sensors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики температуры в доме"""
    sensors = db.query(models.TemperatureSensor).all()
    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": sensor.room.name,
            "value": sensor.value
        }
        for sensor in sensors
    ]

@router.get("/room/{room_id}", response_model=List[schemas.TemperatureSensorResponse])
def get_room_temperature_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить датчики температуры в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors = db.query(models.TemperatureSensor).filter(
        models.TemperatureSensor.room_id == room_id
    ).all()

    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": room.name,
            "value": sensor.value
        }
        for sensor in sensors
    ]