from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Словари для комнат и датчиков
ROOM_TYPES = {
    1: "Прихожая",
    2: "Холл",
    3: "Гостиная",
    4: "Кухня",
    5: "Кухня-гостиная",
    6: "Спальня",
    7: "Техническое помещение",
    8: "Санузел"
}

SENSOR_TYPES = {
    1: "Датчик температуры",
    2: "Датчик освещения",
    3: "Датчик газа",
    4: "Датчик влажности",
    5: "Датчик вентиляции",
    6: "Датчик движения"
}

SENSOR_NAMES = {
    'temperature': 'Датчик температуры',
    'light': 'Датчик освещения',
    'gas': 'Датчик газа',
    'humidity': 'Датчик влажности',
    'fan': 'Датчик вентиляции',
}

# ---------- Пользователь ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
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
    created_room_ids = Column(JSON, nullable=True)
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

    def get_total_sensors(self):
        return (
                len(self.temperature_sensors) +
                len(self.light_sensors) +
                len(self.gas_sensors) +
                len(self.humidity_sensors) +
                len(self.ventilation_sensors)
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
    sensor_id = Column(Integer, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    is_on = Column(Boolean, nullable=False)

    room = relationship("Room", back_populates="light_sensors")


class GasSensor(Base):
    __tablename__ = "gas_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_gas_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    value = Column(Boolean, nullable=True)
    status = Column(String, nullable=False, default="данных нет")

    room = relationship("Room", back_populates="gas_sensors")


class HumiditySensor(Base):
    __tablename__ = "humidity_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_humidity_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    humidity_level = Column(Float, nullable=False)

    room = relationship("Room", back_populates="humidity_sensors")


class VentilationSensor(Base):
    __tablename__ = "ventilation_sensors"
    __table_args__ = (UniqueConstraint('room_id', 'sensor_id', name='uq_room_ventilation_sensor'),)

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    is_on = Column(Boolean, nullable=False)

    room = relationship("Room", back_populates="ventilation_sensors")

# Управление через приложение
class HomeControlMode(Base):
    __tablename__ = "home_control_modes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # True = ручной режим
    # False = автоматический режим
    is_manual = Column(Boolean, default=False, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")

# Температура снаружи
class OutdoorTemperature(Base):
    __tablename__ = "outdoor_temperatures"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    temperatures = Column(JSON, nullable=False)

    min_temperature = Column(Float, nullable=False)
    max_temperature = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")