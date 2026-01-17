from sqlalchemy.orm import Session
from app import models
from datetime import datetime

def create_room_from_application(db: Session, room_id: int) -> models.Room:
    """Создать комнату на основе ID из заявки"""
    if room_id not in models.ROOM_TYPES:
        raise ValueError(f"Invalid room ID: {room_id}")

    room_name = models.ROOM_TYPES[room_id]

    # Проверяем, не существует ли уже комната с таким именем
    existing_room = db.query(models.Room).filter(models.Room.name == room_name).first()
    if existing_room:
        return existing_room

    # Создаем новую комнату
    room = models.Room(name=room_name)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def create_sensor_from_application(db: Session, sensor_type: str, sensor_num: int, room_id: int) -> bool:
    """
    Создать датчик на основе данных из заявки

    Args:
        sensor_type: тип датчика (temperature, light, etc.)
        sensor_num: порядковый номер датчика в комнате (целое число)
        room_id: ID комнаты
    """
    sensor_models = {
        "temperature": models.TemperatureSensor,
        "light": models.LightSensor,
        "gas": models.GasSensor,
        "humidity": models.HumiditySensor,
        "ventilation": models.VentilationSensor,
        "motion": models.MotionSensor
    }

    if sensor_type not in sensor_models:
        return False

    sensor_model = sensor_models[sensor_type]

    # Проверяем, не существует ли уже датчик с таким sensor_num в этой комнате
    existing_sensor = db.query(sensor_model).filter(
        sensor_model.room_id == room_id,
        sensor_model.sensor_id == sensor_num
    ).first()

    if existing_sensor:
        return True  # Датчик уже существует

    # Создаем новый датчик с default значением в зависимости от типа
    if sensor_type == "temperature":
        sensor = sensor_model(
            sensor_id=sensor_num,  # Используем sensor_num как целое число
            room_id=room_id,
            value=20.0  # комнатная температура
        )
    elif sensor_type == "light":
        sensor = sensor_model(
            sensor_id=sensor_num,
            room_id=room_id,
            is_on=False
        )
    elif sensor_type == "gas":
        sensor = sensor_model(
            sensor_id=sensor_num,
            room_id=room_id,
            ppm=400.0,  # нормальный уровень CO2
            status="уличный воздух"
        )
    elif sensor_type == "humidity":
        sensor = sensor_model(
            sensor_id=sensor_num,
            room_id=room_id,
            humidity_level=50.0  # комфортная влажность
        )
    elif sensor_type == "ventilation":
        sensor = sensor_model(
            sensor_id=sensor_num,
            room_id=room_id,
            fan_speed=0.0,
            is_on=False
        )
    elif sensor_type == "motion":
        sensor = sensor_model(
            sensor_id=sensor_num,
            room_id=room_id,
            trigger_time=datetime.utcnow()
        )
    else:
        return False

    db.add(sensor)
    db.commit()
    return True