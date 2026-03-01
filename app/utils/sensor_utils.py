from sqlalchemy.orm import Session
from app import models
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, List, Any


def create_room_from_config(
        db: Session,
        room_type_id: int,
        room_number: int,
        existing_rooms_count: Dict[int, int]
) -> models.Room:
    """
    Создать комнату на основе конфигурации из заявки
    Учитывает уже существующие комнаты в системе

    Args:
        room_type_id: ID типа комнаты из словаря
        room_number: порядковый номер комнаты этого типа в текущей заявке
        existing_rooms_count: словарь с количеством уже существующих комнат каждого типа
    """
    if room_type_id not in models.ROOM_TYPES:
        raise ValueError(f"Invalid room ID: {room_type_id}")

    base_room_name = models.ROOM_TYPES[room_type_id]

    # Определяем общее количество комнат этого типа (существующие + текущая)
    total_count = existing_rooms_count.get(room_type_id, 0) + room_number

    # Формируем уникальное имя комнаты
    if total_count == 1:
        # Если это первая комната данного типа в системе
        room_name = base_room_name
    else:
        # Если есть другие комнаты этого типа
        room_name = f"{base_room_name} {total_count}"

    # Проверяем, не существует ли уже комната с таким именем
    # (на случай, если кто-то вручную создал комнату)
    existing_room = db.query(models.Room).filter(models.Room.name == room_name).first()
    if existing_room:
        # Если комната уже существует, ищем следующее свободное имя
        counter = total_count
        while True:
            counter += 1
            new_name = f"{base_room_name} {counter}"
            existing = db.query(models.Room).filter(models.Room.name == new_name).first()
            if not existing:
                room_name = new_name
                break

    # Создаем новую комнату
    room = models.Room(name=room_name)
    db.add(room)
    db.flush()

    return room


def get_next_sensor_number(db: Session, room_id: int, sensor_type: str) -> int:
    """
    Получить следующий порядковый номер для датчика определенного типа в комнате
    """
    sensor_models = {
        "temperature": models.TemperatureSensor,
        "light": models.LightSensor,
        "gas": models.GasSensor,
        "humidity": models.HumiditySensor,
        "ventilation": models.VentilationSensor,
    }

    if sensor_type not in sensor_models:
        return 1

    sensor_model = sensor_models[sensor_type]

    # Находим максимальный sensor_id для данного типа датчиков в комнате
    max_sensor = db.query(sensor_model).filter(
        sensor_model.room_id == room_id
    ).order_by(sensor_model.sensor_id.desc()).first()

    if max_sensor:
        return max_sensor.sensor_id + 1
    return 1


def create_sensor_from_application(db: Session, sensor_type: str, room_id: int) -> bool:
    """
    Создать датчик на основе данных из заявки

    Args:
        sensor_type: тип датчика (temperature, light, etc.)
        room_id: ID комнаты
    """
    sensor_models = {
        "temperature": models.TemperatureSensor,
        "light": models.LightSensor,
        "gas": models.GasSensor,
        "humidity": models.HumiditySensor,
        "ventilation": models.VentilationSensor,
    }

    if sensor_type not in sensor_models:
        return False

    sensor_model = sensor_models[sensor_type]

    # Получаем следующий порядковый номер для датчика
    next_sensor_num = get_next_sensor_number(db, room_id, sensor_type)

    # Создаем новый датчик с default значением в зависимости от типа
    if sensor_type == "temperature":
        sensor = sensor_model(
            sensor_id=next_sensor_num,
            room_id=room_id,
            value=None
        )
    elif sensor_type == "light":
        sensor = sensor_model(
            sensor_id=next_sensor_num,
            room_id=room_id,
            is_on=False
        )
    elif sensor_type == "gas":
        sensor = sensor_model(
            sensor_id=next_sensor_num,
            room_id=room_id,
            value=False,
            status="данных нет"
        )
    elif sensor_type == "humidity":
        sensor = sensor_model(
            sensor_id=next_sensor_num,
            room_id=room_id,
            humidity_level=None
        )
    elif sensor_type == "ventilation":
        sensor = sensor_model(
            sensor_id=next_sensor_num,
            room_id=room_id,
            is_on=False
        )
    else:
        return False

    db.add(sensor)
    db.flush()
    return True


def get_existing_rooms_count(db: Session) -> Dict[int, int]:
    """
    Получить количество уже существующих комнат каждого типа

    Returns:
        Dict[room_type_id, count]
    """
    result = {}
    all_rooms = db.query(models.Room).all()

    for room in all_rooms:
        # Пытаемся определить тип комнаты по имени
        for type_id, type_name in models.ROOM_TYPES.items():
            if room.name == type_name or room.name.startswith(f"{type_name} "):
                result[type_id] = result.get(type_id, 0) + 1
                break

    return result


def process_application_rooms(
        db: Session,
        rooms_config: List[Dict[str, Any]]
) -> List[int]:
    """
    Обработать все комнаты из заявки и создать их

    Args:
        rooms_config: список конфигураций комнат из заявки
                     [{"room_id": 6, "sensor_ids": [1,2,3]}, ...]

    Returns:
        List[int] - список ID созданных комнат
    """
    created_room_ids = []

    # Получаем информацию о существующих комнатах
    existing_rooms_count = get_existing_rooms_count(db)

    # Счетчики для комнат в текущей заявке
    current_application_counters = {}

    # Маппинг ID типов датчиков в строковые типы
    sensor_type_map = {
        1: "temperature",
        2: "light",
        3: "gas",
        4: "humidity",
        5: "ventilation",
        6: "motion",
    }

    for room_config in rooms_config:
        room_type_id = room_config["room_id"]
        sensor_type_ids = room_config["sensor_ids"]

        # Увеличиваем счетчик для этого типа комнаты в текущей заявке
        current_application_counters[room_type_id] = \
            current_application_counters.get(room_type_id, 0) + 1

        # Создаем комнату
        room = create_room_from_config(
            db,
            room_type_id,
            current_application_counters[room_type_id],
            existing_rooms_count
        )

        created_room_ids.append(room.id)

        # Создаем датчики для этой комнаты
        for sensor_type_id in sensor_type_ids:
            sensor_type_key = sensor_type_map.get(sensor_type_id)
            if sensor_type_key:
                try:
                    create_sensor_from_application(db, sensor_type_key, room.id)
                except Exception as e:
                    print(f"Error creating sensor {sensor_type_key} in room {room.id}: {e}")
                    continue

    return created_room_ids