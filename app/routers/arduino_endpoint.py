from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
import logging

from app.models import SENSOR_NAMES

router = APIRouter(prefix="/arduino", tags=["Arduino Data"])
logger = logging.getLogger(__name__)

'''
Универсальный эндпоинт для приема данных от Arduino.
Принимает все данные от датчиков в комнате одним запросом.
Пример:
{
  "room_id": 1,
  "sensors": [
    {
      "sensor_db_id": 1,
      "type": "temperature",
      "value": 23.5
    },
    {
      "sensor_db_id": 1,
      "type": "humidity",
      "humidity_level": 65.2
    },
    {
      "sensor_db_id": 1,
      "type": "light",
      "is_on": true
    },
    {
      "sensor_db_id": 2,
      "type": "light",
      "is_on": false
    },
    {
      "sensor_db_id": 1,
      "type": "gas",
      "value": true
    }
  ]
}
'''
@router.post("/send-data", response_model=schemas.ArduinoDataResponse)
def receive_arduino_data(
        data: schemas.ArduinoDataCreate,
        db: Session = Depends(get_db)
):
    print('📥 Получены данные от Arduino:')
    print('=' * 50)
    print(data)
    print('=' * 50)

    data_dict = data.model_dump()

    print(f"📍 Комната [ID: {data_dict.get('room_id')}]")
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
            print(f"Вентиляция: {state}")


        else:
            # Для неизвестных типов собираем все не-None значения
            values = []
            for key, value in sensor.items():
                if key not in ['sensor_db_id', 'type'] and value is not None:
                    if key == 'is_on':
                        values.append(f"состояние: {'вкл' if value else 'выкл'}")
                    elif key == 'value':
                        values.append(f"значение: {value}")
                    elif key == 'humidity_level':
                        values.append(f"влажность: {value}%")
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
        models.Room.id == data.room_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"Room with id={data.room_id} not found"
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
            else:
                errors.append(f"Unknown sensor type: {sensor_data.type}")
                continue

            processed_count += 1
            logger.info(f"Processed {sensor_data.type} sensor {sensor_data.sensor_db_id} in room {room.name}")

        except Exception as e:
            error_msg = f"Error processing sensor {sensor_data.sensor_db_id} ({sensor_data.type}): {str(e)}"
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
    if data.value is None:
        raise ValueError("Temperature value is required")

    sensor = db.query(models.TemperatureSensor).filter(
        models.TemperatureSensor.id == data.sensor_db_id,
        models.TemperatureSensor.room_id == room.id
    ).first()

    if not sensor:
        raise ValueError("Temperature sensor not found in this room")

    sensor.value = data.value


def process_light_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    is_on = data.is_on if data.is_on is not None else data.value

    if is_on is None:
        raise ValueError("Light state is required")

    sensor = db.query(models.LightSensor).filter(
        models.LightSensor.id == data.sensor_db_id,
        models.LightSensor.room_id == room.id
    ).first()

    if not sensor:
        raise ValueError("Light sensor not found in this room")

    sensor.is_on = bool(is_on)


def process_gas_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    value = data.value

    if value is None:
        status = "Данных нет"
    elif value is True:
        status = "Повышенное количество CO2"
    else:
        status = "Газ не обнаружен"

    sensor = db.query(models.GasSensor).filter(
        models.GasSensor.id == data.sensor_db_id,
        models.GasSensor.room_id == room.id
    ).first()

    if not sensor:
        raise ValueError("Gas sensor not found in this room")

    sensor.value = value
    sensor.status = status


def process_humidity_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    humidity = data.humidity_level

    if humidity is None:
        raise ValueError("Humidity value is required")

    sensor = db.query(models.HumiditySensor).filter(
        models.HumiditySensor.id == data.sensor_db_id,
        models.HumiditySensor.room_id == room.id
    ).first()

    if not sensor:
        raise ValueError("Humidity sensor not found in this room")

    sensor.humidity_level = float(humidity)


def process_ventilation_sensor(db: Session, room: models.Room, data: schemas.SensorData):
    if data.is_on is None:
        raise ValueError("Ventilation state is required")

    sensor = db.query(models.VentilationSensor).filter(
        models.VentilationSensor.id == data.sensor_db_id,
        models.VentilationSensor.room_id == room.id
    ).first()

    if not sensor:
        raise ValueError("Ventilation sensor not found in this room")

    sensor.is_on = bool(data.is_on)

