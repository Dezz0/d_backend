from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from typing import List

router = APIRouter(prefix="/sensors/ventilation", tags=["Ventilation"])

@router.post("/", response_model=schemas.VentilationSensorResponse)
def add_ventilation_data(
    data: schemas.VentilationSensorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавить/обновить данные датчика вентиляции"""
    # Проверяем, что комната существует (должна быть создана через заявку)
    room = db.query(models.Room).filter(models.Room.name == data.room_name).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room '{data.room_name}' not found. Room must be created through application first."
        )

    # Проверяем, существует ли датчик
    sensor = db.query(models.VentilationSensor).filter(
        models.VentilationSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        # Обновляем существующий датчик
        if sensor.room_id != room.id:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor exists in different room: {sensor.room.name}"
            )
        sensor.fan_speed = data.fan_speed
        sensor.is_on = data.is_on
    else:
        # Создаем новый датчик (только если комната существует)
        sensor = models.VentilationSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            fan_speed=data.fan_speed,
            is_on=data.is_on
        )
        db.add(sensor)

    db.commit()
    db.refresh(sensor)

    return {
        "sensor_id": sensor.sensor_id,
        "room_name": room.name,
        "fan_speed": sensor.fan_speed,
        "is_on": sensor.is_on
    }

@router.get("/list", response_model=List[schemas.VentilationSensorResponse])
def get_all_ventilation_sensors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики вентиляции в доме"""
    sensors = db.query(models.VentilationSensor).all()
    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": sensor.room.name,
            "fan_speed": sensor.fan_speed,
            "is_on": sensor.is_on
        }
        for sensor in sensors
    ]

@router.get("/room/{room_id}", response_model=List[schemas.VentilationSensorResponse])
def get_room_ventilation_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить датчики вентиляции в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors = db.query(models.VentilationSensor).filter(
        models.VentilationSensor.room_id == room_id
    ).all()

    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": room.name,
            "fan_speed": sensor.fan_speed,
            "is_on": sensor.is_on
        }
        for sensor in sensors
    ]