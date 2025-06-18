# --- Archivo: tracking-yape-backend/app/schemas.py ---
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, NotificationStatus  # Importa los Enums


# --- Esquemas para WorkingGroup ---
class WorkingGroupBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class WorkingGroupCreate(WorkingGroupBase):
    pass  # No se necesita creator_id aquí, se obtiene del token


class WorkingGroupOut(WorkingGroupBase):
    id: int
    creator_id: int  # ID del usuario que lo creó

    class Config:
        from_attributes = True


# --- Esquemas para User (ahora incluye campos de personal_data) ---
class UserBase(BaseModel):
    username: str = Field(..., max_length=255)
    dni: Optional[str] = Field(None, max_length=15)
    name: Optional[str] = Field(None, max_length=50)
    maternal_surname: Optional[str] = Field(None, max_length=50)
    paternal_surname: Optional[str] = Field(None, max_length=50)
    is_verified: bool = False
    avatar: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=15)
    country_code: Optional[str] = Field(None, max_length=5)
    is_active: bool = True


class UserCreateOwner(
    UserBase
):  # Para el registro del admin del grupo (crea working_group)
    password: str
    group_name: str = Field(..., max_length=50)  # Nombre del working_group a crear
    # Otros campos de UserBase se heredan.


class UserCreateMember(UserBase):  # Para que el admin agregue miembros
    password: str
    working_group_id: int  # El grupo al que se asigna
    # Otros campos de UserBase se heredan.


class UserOut(UserBase):
    id: int
    role: UserRole
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    # Campos que pueden ser actualizados por el propio usuario o por un admin
    username: Optional[str] = Field(None, max_length=255)
    dni: Optional[str] = Field(None, max_length=15)
    name: Optional[str] = Field(None, max_length=50)
    maternal_surname: Optional[str] = Field(None, max_length=50)
    paternal_surname: Optional[str] = Field(None, max_length=50)
    is_verified: Optional[bool] = None
    avatar: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=15)
    country_code: Optional[str] = Field(None, max_length=5)
    is_active: Optional[bool] = None
    password: Optional[str] = None  # Para cambiar contraseña


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    # El rol ahora se refiere a si es admin del grupo
    role: Optional[UserRole] = None  # ADMIN o MEMBER
    working_group_id: Optional[int] = (
        None  # ID del grupo principal al que pertenece el usuario (o el que creó)
    )
    group_name: Optional[str] = None  # Nombre del working_group


# --- Esquemas para Device ---
class DeviceBase(BaseModel):
    device_uid: str = Field(..., max_length=255)
    alias: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class DeviceCreate(DeviceBase):
    working_group_id: int  # El grupo al que se asigna el dispositivo


class DeviceOut(DeviceBase):
    id: int
    working_group_id: int
    last_seen: Optional[datetime] = None
    last_ip_address: Optional[str] = Field(None, max_length=45)

    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    alias: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


# --- Esquemas para DeviceUser (Tabla de unión) ---
class DeviceUserBase(BaseModel):
    user_id: int
    device_id: int
    is_active: bool = True


class DeviceUserCreate(DeviceUserBase):
    pass


class DeviceUserOut(DeviceUserBase):
    id: int

    class Config:
        from_attributes = True


class DeviceUserUpdate(BaseModel):
    is_active: Optional[bool] = None


# --- Esquemas para Horarios (Individual y Grupo) ---
class ScheduleBase(BaseModel):
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    is_active: bool = True


class IndividualScheduleCreate(ScheduleBase):
    # Necesita al menos uno de estos para ser válido
    device_user_id: Optional[int] = None
    device_id: Optional[int] = None
    user_id: Optional[int] = None


class IndividualScheduleOut(ScheduleBase):
    id: int
    device_user_id: Optional[int] = None
    device_id: Optional[int] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


class GroupScheduleCreate(ScheduleBase):
    # working_group_id se obtiene del token o de la ruta
    pass


class GroupScheduleOut(ScheduleBase):
    id: int
    working_group_id: int

    class Config:
        from_attributes = True


class ScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    is_active: Optional[bool] = None


# --- Esquemas para Notification ---
class NotificationBase(BaseModel):
    raw_notification: str
    name: str = Field(..., max_length=255)
    amount: float
    security_code: str = Field(..., max_length=255)
    notification_timestamp: datetime  # Fecha y hora de detección en el cliente


class NotificationCreate(NotificationBase):
    # working_group_id se obtiene del token del servicio de notificaciones
    pass


class NotificationOut(NotificationBase):
    id: int
    working_group_id: int
    status: NotificationStatus  # recieved o sent
    created_at: datetime  # Cuando se guardó en el backend

    class Config:
        from_attributes = True


class NotificationUpdateStatus(BaseModel):
    status: NotificationStatus


# --- Esquemas para DeviceUserNotification (para evitar duplicados MQTT) ---
class DeviceUserNotificationBase(BaseModel):
    notification_id: int
    device_id: int
    user_id: int
    is_active: bool = True  # Podría ser `is_sent: bool` y `sent_at: datetime`


class DeviceUserNotificationCreate(DeviceUserNotificationBase):
    pass


class DeviceUserNotificationOut(DeviceUserNotificationBase):
    id: int
    sent_at: datetime  # Cuando se registró el intento de envío MQTT

    class Config:
        from_attributes = True
