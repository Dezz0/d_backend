from typing import Optional, List, Dict, Union

from pydantic import BaseModel
from datetime import datetime
from enum import Enum

# ---------- Пользователь ----------
class UserBase(BaseModel):
    login: str

class UserResponse(UserBase):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    application_submitted: bool
    has_pending_application: bool

    class Config:
        orm_mode = True

class UserProfileResponse(UserBase):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    application_submitted: bool
    created_at: datetime
    total_applications: int = 0
    pending_applications: int = 0
    approved_applications: int = 0
    rejected_applications: int = 0
    total_rooms: int = 0
    total_sensors: int = 0

    class Config:
        orm_mode = True

class ProfileStatsResponse(BaseModel):
    total_applications: int
    pending_applications: int
    approved_applications: int
    rejected_applications: int
    total_rooms: int
    total_sensors: int

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

class UserAuth(BaseModel):
    login: str
    password: str

class UserCreate(UserAuth):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshToken(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    login: Optional[str] = None
    is_admin: Optional[bool] = None
    application_submitted: Optional[bool] = None
    has_pending_application: Optional[bool] = None

# ---------- Пользователи (для админа) ----------
class UserListResponse(BaseModel):
    id: int
    login: str
    is_active: bool
    is_admin: bool
    application_submitted: bool
    applications_count: int
    pending_applications: int
    approved_applications: int
    rejected_applications: int
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# ---------- Заявки ----------
class ApplicationBase(BaseModel):
    rooms: List[int]  # ID комнат из словаря
    sensors: Dict[int, List[int]]  # {room_id: [sensor_ids]}

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    status: str
    rejection_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_login: str

    class Config:
        orm_mode = True

class ApplicationUpdate(BaseModel):
    status: str  # approved, rejected
    rejection_comment: Optional[str] = None


# ---------- Справочники ----------
class DictionariesResponse(BaseModel):
    rooms: Dict[int, str]
    sensors: Dict[int, str]

# ---------- Комнаты ----------
class RoomBase(BaseModel):
    name: str

class RoomResponse(RoomBase):
    id: int

    class Config:
        orm_mode = True

class SensorInfo(BaseModel):
    id: int  # Изменено с str на int
    type: str # temperature, light, gas, humidity, ventilation, motion
    name: str
    room_id: int
    room_name: str

# ---------- Комнаты пользователя ----------
class UserRoomsResponse(BaseModel):
    id: int
    name: str
    sensors: List[SensorInfo] = []

# ---------- Температура ----------
class TemperatureSensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    value: float

class TemperatureSensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    value: float

    class Config:
        orm_mode = True

# ---------- Свет ----------
class LightSensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    is_on: bool

class LightSensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    is_on: bool

    class Config:
        orm_mode = True

# ---------- Угарный газ ----------
class GasStatus(str, Enum):
    NORMAL = "уличный воздух"
    RECOMMENDED = "рекомендованная концентрация"
    WARNING = "предельная концентрация"
    DANGER = "смертельная концентрация"

class GasSensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    ppm: float

class GasSensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    ppm: float
    status: str

    class Config:
        orm_mode = True

# ---------- Влажность ----------
class HumiditySensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    humidity_level: float

class HumiditySensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    humidity_level: float

    class Config:
        orm_mode = True

# ---------- Вентиляция ----------
class VentilationSensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    fan_speed: float
    is_on: bool

class VentilationSensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    fan_speed: float
    is_on: bool

    class Config:
        orm_mode = True

# ---------- Движение ----------
class MotionSensorCreate(BaseModel):
    sensor_id: str
    room_name: str
    trigger_time: datetime

class MotionSensorResponse(BaseModel):
    sensor_id: str
    room_name: str
    trigger_time: datetime

    class Config:
        orm_mode = True

# ---------- Новые схемы для универсального эндпоинта ----------
class SensorData(BaseModel):
    """Данные от одного датчика"""
    sensor_id: int  # Уникальный ID датчика в комнате
    type: str  # temperature, light, gas, humidity, ventilation, motion
    value: Optional[Union[float, bool, str, int]] = None
    is_on: Optional[bool] = None
    ppm: Optional[float] = None
    humidity_level: Optional[float] = None
    fan_speed: Optional[float] = None
    trigger_time: Optional[datetime] = None

class ArduinoDataCreate(BaseModel):
    """Данные от Arduino для всех датчиков в комнате"""
    room_id: int  # Уникальный ID комнаты
    room_name: str  # Название комнаты для проверки
    sensors: List[SensorData]  # Все датчики в комнате

class ArduinoDataResponse(BaseModel):
    """Ответ на успешную обработку данных от Arduino"""
    room_id: int
    room_name: str
    processed_sensors: int
    success: bool
    message: str
