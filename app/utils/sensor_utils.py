from sqlalchemy.orm import Session
from app import models
from typing import Dict, List, Any

def process_application_rooms(
    db: Session,
    user_id: int,
    rooms_config: List[dict]
) -> List[int]:

    created_room_ids = []

    for room_config in rooms_config:

        room_type = room_config.get("room_type")
        sensor_ids = room_config.get("sensor_ids", [])

        if not room_type:
            raise Exception(f"Invalid room config: {room_config}")

        room = models.Room(
            user_id=user_id,
            name=room_type,
            room_type=room_type
        )

        db.add(room)
        db.flush()

        created_room_ids.append(room.id)

        for sensor_type_id in sensor_ids:
            create_sensor_by_id(db, room.id, sensor_type_id)

    return created_room_ids

def create_sensor_by_id(db: Session, room_id: int, sensor_type_id: int):

    sensor_map = {
        1: models.TemperatureSensor,
        2: models.LightSensor,
        3: models.GasSensor,
        4: models.HumiditySensor,
        5: models.VentilationSensor,
    }

    model = sensor_map.get(sensor_type_id)

    if not model:
        raise Exception(f"Unknown sensor type id: {sensor_type_id}")

    sensor = model(room_id=room_id)
    db.add(sensor)