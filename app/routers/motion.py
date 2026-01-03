from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from typing import List

router = APIRouter(prefix="/sensors/motion", tags=["Motion"])

@router.post("/", response_model=schemas.MotionSensorResponse)
def add_motion_data(
    data: schemas.MotionSensorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавить/обновить данные датчика движения"""
    # Проверяем, что комната существует (должна быть создана через заявку)
    room = db.query(models.Room).filter(models.Room.name == data.room_name).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room '{data.room_name}' not found. Room must be created through application first."
        )

    # Проверяем, существует ли датчик
    sensor = db.query(models.MotionSensor).filter(
        models.MotionSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        # Обновляем существующий датчик
        if sensor.room_id != room.id:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor exists in different room: {sensor.room.name}"
            )
        sensor.trigger_time = data.trigger_time
    else:
        # Создаем новый датчик (только если комната существует)
        sensor = models.MotionSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            trigger_time=data.trigger_time
        )
        db.add(sensor)

    db.commit()
    db.refresh(sensor)

    return {
        "sensor_id": sensor.sensor_id,
        "room_name": room.name,
        "trigger_time": sensor.trigger_time
    }

@router.get("/list", response_model=List[schemas.MotionSensorResponse])
def get_all_motion_sensors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики движения в доме"""
    sensors = db.query(models.MotionSensor).all()
    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": sensor.room.name,
            "trigger_time": sensor.trigger_time
        }
        for sensor in sensors
    ]

@router.get("/room/{room_id}", response_model=List[schemas.MotionSensorResponse])
def get_room_motion_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить датчики движения в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors = db.query(models.MotionSensor).filter(
        models.MotionSensor.room_id == room_id
    ).all()

    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": room.name,
            "trigger_time": sensor.trigger_time
        }
        for sensor in sensors
    ]