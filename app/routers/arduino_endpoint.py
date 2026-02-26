from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from datetime import datetime
import logging

from app.models import SENSOR_NAMES

router = APIRouter(prefix="/arduino", tags=["Arduino Data"])
logger = logging.getLogger(__name__)


@router.post("/send-data", response_model=schemas.ArduinoDataResponse)
def receive_arduino_data(
        data: schemas.ArduinoDataCreate,
        db: Session = Depends(get_db)
):
    """
    Универсальный эндпоинт для приема данных от Arduino.
    Принимает все данные от датчиков в комнате одним запросом.
    """

    print('📥 Получены данные от Arduino:')
    print('=' * 50)
    print(data)
    print('=' * 50)

    data_dict = data.model_dump()

    print(f"📍 Комната: {data_dict.get('room_name')} [ID: {data_dict.get('room_id')}]")
    print('─' * 50)

    for sensor in data_dict.get('sensors', []):
        sensor_type = sensor.get('type')  # теперь это строка, например 'temperature'
        sensor_name = SENSOR_NAMES.get(sensor_type, f"Датчик {sensor_type}")

        # Формируем строку с данными в зависимости от типа датчика
        if sensor_type == 'temperature':  # Датчик температуры
            value = sensor.get('value')
            print(f"{sensor_name}: {value}°C" if value else f"{sensor_name}: нет данных")

        elif sensor_type == 'light':  # Датчик освещения
            state = "ВКЛЮЧЕН" if sensor.get('is_on') else "ВЫКЛЮЧЕН"
            print(f"{sensor_name}: {state}")

        elif sensor_type == 'gas':  # Датчик газа
            state = "ЗАГАЗОВАННОСТЬ" if sensor.get('is_on') else "ГАЗ В НОРМЕ"
            print(f"{sensor_name}: {state}")

        elif sensor_type == 'humidity':  # Датчик влажности
            humidity = sensor.get('humidity_level')
            if humidity:
                print(f"{sensor_name}: {humidity}%")
            else:
                print(f"{sensor_name}: нет данных")

        elif sensor_type == 'fan':  # Датчик вентиляции
            state = "ВКЛЮЧЕН" if sensor.get('is_on') else "ВЫКЛЮЧЕН"
            speed = f", скорость: {sensor.get('fan_speed')}" if sensor.get('fan_speed') else ""
            print(f"Вентиляция: {state}{speed}")

        elif sensor_type == 'motion':  # Датчик движения
            is_motion = sensor.get('is_on')
            state = "ДВИЖЕНИЕ ОБНАРУЖЕНО" if is_motion else "НЕТ ДВИЖЕНИЯ"
            print(f"{sensor_name}: {state}")

        else:
            # Для неизвестных типов собираем все не-None значения
            values = []
            for key, value in sensor.items():
                if key not in ['sensor_id', 'type'] and value is not None:
                    if key == 'is_on':
                        values.append(f"состояние: {'вкл' if value else 'выкл'}")
                    elif key == 'value':
                        values.append(f"значение: {value}")
                    elif key == 'humidity_level':
                        values.append(f"влажность: {value}%")
                    elif key == 'fan_speed':
                        values.append(f"скорость: {value}")
                    elif key == 'trigger_time':
                        values.append(f"время: {value}")
                    else:
                        values.append(f"{key}: {value}")

            if values:
                print(f"{sensor_name}: {', '.join(values)}")
            else:
                print(f"{sensor_name}: нет данных")

    print('=' * 50)
    # Проверяем, что комната существует
    room = db.query(models.Room).filter(
        models.Room.id == data.room_id,
        models.Room.name == data.room_name
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room with id={data.room_id} and name='{data.room_name}' not found"
        )

    processed_count = 0
    errors = []

    # Обрабатываем каждый датчик
    for sensor_data in data.sensors:
        try:
            if sensor_data.type == "temperature":
                process_temperature_sensor(db, room, sensor_data)
            elif sensor_data.type == "light":
                process_light_sensor(db, room, sensor_data)
            elif sensor_data.type == "gas":
                process_gas_sensor(db, room, sensor_data)
            elif sensor_data.type == "humidity":
                process_humidity_sensor(db, room, sensor_data)
            elif sensor_data.type == "ventilation":
                process_ventilation_sensor(db, room, sensor_data)
            elif sensor_data.type == "motion":
                process_motion_sensor(db, room, sensor_data)
            else:
                errors.append(f"Unknown sensor type: {sensor_data.type}")
                continue

            processed_count += 1
            logger.info(f"Processed {sensor_data.type} sensor {sensor_data.sensor_id} in room {room.name}")

        except Exception as e:
            error_msg = f"Error processing sensor {sensor_data.sensor_id} ({sensor_data.type}): {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

    db.commit()

    return {
        "room_id": room.id,
        "room_name": room.name,
        "processed_sensors": processed_count,
        "success": len(errors) == 0,
        "message": f"Processed {processed_count} sensors" +
                   (f", errors: {len(errors)}" if errors else "")
    }


# Функции обработки для каждого типа датчика
def process_temperature_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика температуры"""
    if data.value is None:
        raise ValueError("Temperature value is required")

    sensor = db.query(models.TemperatureSensor).filter(
        models.TemperatureSensor.room_id == room.id,
        models.TemperatureSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.value = data.value
    else:
        sensor = models.TemperatureSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            value=data.value
        )
        db.add(sensor)


def process_light_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика освещения"""
    is_on = data.is_on if data.is_on is not None else data.value

    if is_on is None:
        raise ValueError("Light state (is_on or value) is required")

    sensor = db.query(models.LightSensor).filter(
        models.LightSensor.room_id == room.id,
        models.LightSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.is_on = bool(is_on)
    else:
        sensor = models.LightSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            is_on=bool(is_on)
        )
        db.add(sensor)


def process_gas_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика газа"""
    ppm = data.ppm if data.ppm is not None else data.value

    if ppm is None:
        raise ValueError("Gas PPM value is required")

    # Определяем статус по PPM
    if ppm <= 400:
        status = "уличный воздух"
    elif ppm <= 1000:
        status = "рекомендованная концентрация"
    elif ppm <= 1500:
        status = "предельная концентрация"
    else:
        status = "смертельная концентрация"

    sensor = db.query(models.GasSensor).filter(
        models.GasSensor.room_id == room.id,
        models.GasSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.ppm = float(ppm)
        sensor.status = status
    else:
        sensor = models.GasSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            ppm=float(ppm),
            status=status
        )
        db.add(sensor)


def process_humidity_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика влажности"""
    humidity = data.humidity_level if data.humidity_level is not None else data.value

    if humidity is None:
        raise ValueError("Humidity value is required")

    sensor = db.query(models.HumiditySensor).filter(
        models.HumiditySensor.room_id == room.id,
        models.HumiditySensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.humidity_level = float(humidity)
    else:
        sensor = models.HumiditySensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            humidity_level=float(humidity)
        )
        db.add(sensor)


def process_ventilation_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика вентиляции"""
    fan_speed = data.fan_speed if data.fan_speed is not None else data.value
    is_on = data.is_on

    if fan_speed is None or is_on is None:
        raise ValueError("Ventilation fan_speed and is_on are required")

    sensor = db.query(models.VentilationSensor).filter(
        models.VentilationSensor.room_id == room.id,
        models.VentilationSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.fan_speed = float(fan_speed)
        sensor.is_on = bool(is_on)
    else:
        sensor = models.VentilationSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            fan_speed=float(fan_speed),
            is_on=bool(is_on)
        )
        db.add(sensor)


def process_motion_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    """Обработка датчика движения"""
    trigger_time = data.trigger_time or datetime.now()

    sensor = db.query(models.MotionSensor).filter(
        models.MotionSensor.room_id == room.id,
        models.MotionSensor.sensor_id == data.sensor_id
    ).first()

    if sensor:
        sensor.trigger_time = trigger_time
    else:
        sensor = models.MotionSensor(
            sensor_id=data.sensor_id,
            room_id=room.id,
            trigger_time=trigger_time
        )
        db.add(sensor)
