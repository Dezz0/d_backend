from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/sensors", tags=["Sensors"])

SENSOR_MODELS = {
    "temperature": models.TemperatureSensor,
    "light": models.LightSensor,
    "gas": models.GasSensor,
    "humidity": models.HumiditySensor,
    "ventilation": models.VentilationSensor,
    "motion": models.MotionSensor
}

# ---------- Все датчики в комнате ----------
@router.get("/room/{room_id}")
def get_room_sensors(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все датчики в конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sensors_data = {
        "room_id": room.id,
        "room_name": room.name,
        "temperature_sensors": room.temperature_sensors,
        "light_sensors": room.light_sensors,
        "gas_sensors": room.gas_sensors,
        "humidity_sensors": room.humidity_sensors,
        "ventilation_sensors": room.ventilation_sensors,
        "motion_sensors": room.motion_sensors
    }

    return sensors_data

# ---------- Информация о конкретном датчике ----------
@router.get("/{sensor_type}/{sensor_id}")
def get_sensor_info(
    sensor_type: str,
    sensor_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if sensor_type not in SENSOR_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor type. Available types: {list(SENSOR_MODELS.keys())}"
        )

    sensor_model = SENSOR_MODELS[sensor_type]
    sensor = db.query(sensor_model).filter_by(sensor_id=sensor_id).first()

    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    return sensor