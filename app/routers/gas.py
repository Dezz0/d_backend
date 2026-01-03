from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from typing import List

router = APIRouter(prefix="/sensors/gas", tags=["Gas"])

def get_gas_status(ppm: float) -> str:
    if ppm <= 9:
        return schemas.GasStatus.NORMAL
    elif ppm <= 35:
        return schemas.GasStatus.RECOMMENDED
    elif ppm <= 100:
        return schemas.GasStatus.WARNING
    else:
        return schemas.GasStatus.DANGER

@router.post("/", response_model=schemas.GasSensorResponse)
def add_gas_data(
    data: schemas.GasSensorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавить/обновить данные датчика газа"""
    # Проверяем, что комната существует (должна быть создана через заявку)
    room = db.query(models.Room).filter(models.Room.name == data.room_name).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room '{data.room_name}' not found. Room must be created through application first."
        )

    # Определяем статус газа
    gas_status = get_gas_status(data.ppm)

    # Проверяем, существует ли датчик
    sensor = db.query(models.GasSensor).filter(
        models.GasSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        # Обновляем существующий датчик
        if sensor.room_id != room.id:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor exists in different room: {sensor.room.name}"
            )
        sensor.ppm = data.ppm
        sensor.status = gas_status
    else:
        # Создаем новый датчик (только если комната существует)
        sensor = models.GasSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            ppm=data.ppm,
            status=gas_status
        )
        db.add(sensor)

    db.commit()
    db.refresh(sensor)

    return {
        "sensor_id": sensor.sensor_id,
        "room_name": room.name,
        "ppm": sensor.ppm,
        "status": sensor.status
    }

@router.get("/list", response_model=List[schemas.GasSensorResponse])
def get_all_gas_sensors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики газа в доме"""
    sensors = db.query(models.GasSensor).all()
    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": sensor.room.name,
            "ppm": sensor.ppm,
            "status": sensor.status
        }
        for sensor in sensors
    ]

@router.get("/room/{room_id}", response_model=List[schemas.GasSensorResponse])
def get_room_gas_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить датчики газа в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors = db.query(models.GasSensor).filter(
        models.GasSensor.room_id == room_id
    ).all()

    return [
        {
            "sensor_id": sensor.sensor_id,
            "room_name": room.name,
            "ppm": sensor.ppm,
            "status": sensor.status
        }
        for sensor in sensors
    ]