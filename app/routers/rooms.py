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
    "motion": models.MotionSensor
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
        if room.motion_sensors:
            sensors_info.append({"type": "motion", "count": len(room.motion_sensors)})

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
        for sensor in room.temperature_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "temperature",
                    "name": "Датчик температуры",
                    "room_id": room.id,
                    "room_name": room.name
                })

        # Датчики освещения
        for sensor in room.light_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "light",
                    "name": "Датчик освещения",
                    "room_id": room.id,
                    "room_name": room.name
                })

        # Датчики газа
        for sensor in room.gas_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "gas",
                    "name": "Датчик газа",
                    "room_id": room.id,
                    "room_name": room.name
                })

        # Датчики влажности
        for sensor in room.humidity_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "humidity",
                    "name": "Датчик влажности",
                    "room_id": room.id,
                    "room_name": room.name
                })

        # Датчики вентиляции
        for sensor in room.ventilation_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "ventilation",
                    "name": "Датчик вентиляции",
                    "room_id": room.id,
                    "room_name": room.name
                })

        # Датчики движения
        for sensor in room.motion_sensors:
            if str(current_user.id) in sensor.sensor_id:
                sensors.append({
                    "id": sensor.sensor_id,
                    "type": "motion",
                    "name": "Датчик движения",
                    "room_id": room.id,
                    "room_name": room.name
                })

        rooms_data.append({
            "id": room.id,
            "name": room.name,
            "sensors": sensors
        })

    return rooms_data