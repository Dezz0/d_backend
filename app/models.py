from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Словари для комнат и датчиков
ROOM_TYPES = {
    1: "Прихожая",
    2: "Гостиная",
    3: "Кухня",
    4: "Спальня",
    5: "Ванная",
    6: "Туалет",
    7: "Балкон",
    8: "Коридор",
    9: "Кабинет",
    10: "Детская"
}

SENSOR_TYPES = {
    1: "Датчик температуры",
    2: "Датчик освещения",
    3: "Датчик газа",
    4: "Датчик влажности",
    5: "Датчик вентиляции",
    6: "Датчик движения"
}

# ---------- Пользователь ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)  # Новое поле: имя
    last_name = Column(String, nullable=True)   # Новое поле: фамилия
    middle_name = Column(String, nullable=True) # Новое поле: отчество
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    application_submitted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="user")

# ---------- Заявка ----------
class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    rooms = Column(JSON, nullable=False)
    sensors = Column(JSON, nullable=False)
    created_room_ids = Column(JSON, nullable=True)  # Новое поле для хранения ID созданных комнат
    status = Column(String, default="pending")
    rejection_comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")


# ---------- Комнаты ----------
class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    # связи с датчиками
    temperature_sensors = relationship("TemperatureSensor", back_populates="room")
    light_sensors = relationship("LightSensor", back_populates="room")
    gas_sensors = relationship("GasSensor", back_populates="room")
    humidity_sensors = relationship("HumiditySensor", back_populates="room")
    ventilation_sensors = relationship("VentilationSensor", back_populates="room")
    motion_sensors = relationship("MotionSensor", back_populates="room")

    def get_total_sensors(self):
        return (
                len(self.temperature_sensors) +
                len(self.light_sensors) +
                len(self.gas_sensors) +
                len(self.humidity_sensors) +
                len(self.ventilation_sensors) +
                len(self.motion_sensors)
        )

# ---------- Датчики ----------
class TemperatureSensor(Base):
    __tablename__ = "temperature_sensors"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено с String на Integer
    room_id = Column(Integer, ForeignKey("rooms.id"))
    value = Column(Float, nullable=False)

    room = relationship("Room", back_populates="temperature_sensors")

    # Добавить уникальность комбинации room_id + sensor_id
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_temp_sensor'),)


class LightSensor(Base):
    __tablename__ = "light_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_light_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено
    room_id = Column(Integer, ForeignKey("rooms.id"))
    is_on = Column(Boolean, nullable=False)

    room = relationship("Room", back_populates="light_sensors")


class GasSensor(Base):
    __tablename__ = "gas_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_gas_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено
    room_id = Column(Integer, ForeignKey("rooms.id"))
    ppm = Column(Float, nullable=False)
    status = Column(String, nullable=False)

    room = relationship("Room", back_populates="gas_sensors")


class HumiditySensor(Base):
    __tablename__ = "humidity_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_humidity_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено
    room_id = Column(Integer, ForeignKey("rooms.id"))
    humidity_level = Column(Float, nullable=False)

    room = relationship("Room", back_populates="humidity_sensors")


class VentilationSensor(Base):
    __tablename__ = "ventilation_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_ventilation_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено
    room_id = Column(Integer, ForeignKey("rooms.id"))
    fan_speed = Column(Float, nullable=False)
    is_on = Column(Boolean, nullable=False)

    room = relationship("Room", back_populates="ventilation_sensors")


class MotionSensor(Base):
    __tablename__ = "motion_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_motion_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)  # Изменено
    room_id = Column(Integer, ForeignKey("rooms.id"))
    trigger_time = Column(DateTime, nullable=False)

    room = relationship("Room", back_populates="motion_sensors")