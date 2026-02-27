from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/rooms", tags=["Rooms"])

SENSOR_MODELS = {
    "temperature": models.TemperatureSensor,
    "light": models.LightSensor,
    "gas": models.GasSensor,
    "humidity": models.HumiditySensor,
    "ventilation": models.VentilationSensor,
}

@router.get("/", response_model=list[schemas.RoomResponse])
def get_rooms(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Получить список всех комнат с датчиками"""
    rooms = db.query(models.Room).all()

    result = []
    for room in rooms:
        sensors_info = []

        # Собираем информацию по типам датчиков
        if room.temperature_sensors:
            sensors_info.append({"type": "temperature", "count": len(room.temperature_sensors)})
        if room.light_sensors:
            sensors_info.append({"type": "light", "count": len(room.light_sensors)})
        if room.gas_sensors:
            sensors_info.append({"type": "gas", "count": len(room.gas_sensors)})
        if room.humidity_sensors:
            sensors_info.append({"type": "humidity", "count": len(room.humidity_sensors)})
        if room.ventilation_sensors:
            sensors_info.append({"type": "ventilation", "count": len(room.ventilation_sensors)})


        result.append({
            "id": room.id,
            "name": room.name,
            "sensors": sensors_info
        })

    return result

@router.get("/{room_id}", response_model=schemas.RoomResponse)
def get_room_by_id(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить информацию о конкретной комнате"""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.get("/stats", response_model=schemas.ProfileStatsResponse)
def get_rooms_stats(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Получить статистику по комнатам и датчикам пользователя"""
    # Находим одобренную заявку пользователя
    approved_application = db.query(models.Application).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "approved"
    ).first()

    total_rooms = 0
    total_sensors = 0

    if approved_application:
        total_rooms = len(approved_application.rooms)
        total_sensors = sum(len(sensors) for sensors in approved_application.sensors.values())

    return {
        "total_rooms": total_rooms,
        "total_sensors": total_sensors,
        "total_applications": 0,  # Заполнятся отдельно
        "pending_applications": 0,
        "approved_applications": 0,
        "rejected_applications": 0
    }


@router.get("/user/rooms", response_model=list[schemas.UserRoomsResponse])
def get_user_rooms(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Получить комнаты и датчики пользователя (только одобренные заявки)"""
    # Находим одобренную заявку пользователя
    approved_application = db.query(models.Application).filter(
        models.Application.user_id == current_user.id,
        models.Application.status == "approved"
    ).first()

    if not approved_application:
        return []

    rooms_data = []

    # Используем ID созданных комнат из заявки
    # Если created_room_ids нет, используем старый метод (для обратной совместимости)
    if approved_application.created_room_ids:
        room_ids = approved_application.created_room_ids
    else:
        # Для старых заявок создаем комнаты на лету
        room_ids = []
        for room_type_id in approved_application.rooms:
            room = db.query(models.Room).filter(
                models.Room.name == models.ROOM_TYPES.get(room_type_id, "")
            ).first()
            if room:
                room_ids.append(room.id)

    for room_id in room_ids:
        room = db.query(models.Room).filter(models.Room.id == room_id).first()
        if not room:
            continue

        sensors = []

        # Температурные датчики
        for idx, sensor in enumerate(room.temperature_sensors, start=1):
            sensors.append(schemas.SensorInfo(
                id=sensor.sensor_id,  # Это теперь число
                type="temperature",
                name=f"Датчик температуры {idx}",
                room_id=room.id,
                room_name=room.name
            ))

        # Датчики освещения
        for idx, sensor in enumerate(room.light_sensors, start=1):
            sensors.append(schemas.SensorInfo(
                id=sensor.sensor_id,
                type="light",
                name=f"Датчик освещения {idx}",
                room_id=room.id,
                room_name=room.name
            ))

        # Датчики газа
        for idx, sensor in enumerate(room.gas_sensors, start=1):
            sensors.append(schemas.SensorInfo(
                id=sensor.sensor_id,
                type="gas",
                name=f"Датчик газа {idx}",
                room_id=room.id,
                room_name=room.name
            ))

        # Датчики влажности
        for idx, sensor in enumerate(room.humidity_sensors, start=1):
            sensors.append(schemas.SensorInfo(
                id=sensor.sensor_id,
                type="humidity",
                name=f"Датчик влажности {idx}",
                room_id=room.id,
                room_name=room.name
            ))

        # Датчики вентиляции
        for idx, sensor in enumerate(room.ventilation_sensors, start=1):
            sensors.append(schemas.SensorInfo(
                id=sensor.sensor_id,
                type="ventilation",
                name=f"Датчик вентиляции {idx}",
                room_id=room.id,
                room_name=room.name
            ))


        rooms_data.append(schemas.UserRoomsResponse(
            id=room.id,
            name=room.name,
            sensors=sensors
        ))

    return rooms_data

"""Получить комнаты и датчики пользователя для arduino"""
@router.get("/{room_id}/devices", response_model=schemas.RoomDevicesResponse)
def get_room_devices(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    devices = {}

    for light in room.light_sensors:
        devices[light.sensor_id] = {
            "type": "light",
            "is_on": light.is_on
        }

    for fan in room.ventilation_sensors:
        devices[fan.sensor_id] = {
            "type": "ventilation",
            "is_on": fan.is_on
        }

    return {
        "room_id": room.id,
        "room_name": room.name,
        "devices": devices
    }