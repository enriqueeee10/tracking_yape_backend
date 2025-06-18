from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from enum import Enum as PyEnum


# Enum para los roles de usuario (admin del grupo, o miembro normal)
class UserRole(PyEnum):
    ADMIN = "admin"
    MEMBER = "member"


# Enum para el estado de la notificación
class NotificationStatus(PyEnum):
    RECEIVED = "received"
    SENT = "sent"  # Cuando se envía por MQTT


# Tabla: working_groups
class DBWorkingGroup(Base):
    __tablename__ = "working_groups"
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # El usuario que crea el grupo es el admin
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    creator = relationship(
        "DBUser", back_populates="created_working_groups", foreign_keys=[creator_id]
    )
    members = relationship(
        "DBUser", secondary="device_users", back_populates="member_of_working_groups"
    )
    devices = relationship("DBDevice", back_populates="working_group")
    group_schedules = relationship("DBGroupSchedule", back_populates="working_group")
    notifications = relationship(
        "DBNotification", back_populates="working_group"
    )  # Las notificaciones ahora están asociadas a un grupo


# Tabla: users (Ahora unificado para personal_data y users)
# Se asume que personal_data es parte del modelo de usuario o que ciertos campos se manejan aquí.
# Si 'dni', 'name', 'maternal_surname', 'paternal_surname', 'is_verified' son campos del usuario,
# los incorporamos directamente.
class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    # Rol dentro del sistema (puede ser ADMIN de un grupo o MEMBER de varios)
    # Nota: El 'creator_id' en working_groups determinará quién es el ADMIN de ESE grupo.
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)

    # Campos que antes estaban en personal_data
    dni = Column(String(15), unique=True, nullable=True)
    name = Column(String(50), nullable=True)
    maternal_surname = Column(String(50), nullable=True)
    paternal_surname = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    avatar = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(
        String(15), nullable=True
    )  # Considerando números de teléfono con prefijo
    country_code = Column(String(5), nullable=True)  # Ej: +51
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    created_working_groups = relationship(
        "DBWorkingGroup",
        back_populates="creator",
        foreign_keys="[DBWorkingGroup.creator_id]",
    )
    member_of_working_groups = relationship(
        "DBWorkingGroup", secondary="device_users", back_populates="members"
    )
    # Dispositivos asociados directamente a este usuario (si aplica, o a través de device_users)
    user_devices = relationship("DBDeviceUser", back_populates="user")
    user_notifications = relationship("DBDeviceUserNotification", back_populates="user")


# Tabla: devices
class DBDevice(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    working_group_id = Column(
        Integer, ForeignKey("working_groups.id"), nullable=False
    )  # Un dispositivo pertenece a un grupo
    device_uid = Column(
        String(255), unique=True, index=True, nullable=False
    )  # UID único del ESP32
    alias = Column(String(50), nullable=True)  # Nombre amigable
    description = Column(String(255), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    last_ip_address = Column(String(45), nullable=True)  # IPv6 podría ser más larga
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    working_group = relationship("DBWorkingGroup", back_populates="devices")
    device_users = relationship("DBDeviceUser", back_populates="device")
    individual_schedules = relationship("DBIndividualSchedule", back_populates="device")
    device_notifications = relationship(
        "DBDeviceUserNotification", back_populates="device"
    )


# Tabla: device_users (Tabla de unión entre users y devices, y que también lleva el rol)
class DBDeviceUser(Base):
    __tablename__ = "device_users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    user = relationship("DBUser", back_populates="user_devices")
    device = relationship("DBDevice", back_populates="device_users")


# Tabla: individual_schedules (para horarios específicos de dispositivos/usuarios)
class DBIndividualSchedule(Base):
    __tablename__ = "individual_schedules"
    id = Column(Integer, primary_key=True, index=True)
    device_user_id = Column(
        Integer, ForeignKey("device_users.id"), nullable=True
    )  # Puede ser un horario para un dispositivo_usuario específico
    device_id = Column(
        Integer, ForeignKey("devices.id"), nullable=True
    )  # O solo para un dispositivo (si no está vinculado a un usuario en ese contexto)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # O solo para un usuario (si un usuario puede tener su propio horario sin un dispositivo específico)

    # Al menos uno de los tres Foreign Keys (device_user_id, device_id, user_id) debe ser NO NULO
    # Esto se puede validar a nivel de aplicación o con un CHECK constraint en la BD.

    start_time = Column(
        DateTime, nullable=False
    )  # Usamos DateTime para manejar fecha y hora combinadas
    end_time = Column(DateTime, nullable=False)
    all_day = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    device_user = relationship("DBDeviceUser")  # Si se asocia a un device_user
    device = relationship(
        "DBDevice", back_populates="individual_schedules", foreign_keys=[device_id]
    )
    user = relationship("DBUser", foreign_keys=[user_id])


# Tabla: group_schedules (horarios por defecto del grupo)
class DBGroupSchedule(Base):
    __tablename__ = "group_schedules"
    id = Column(Integer, primary_key=True, index=True)
    working_group_id = Column(Integer, ForeignKey("working_groups.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    all_day = Column(
        Boolean, default=True, nullable=False
    )  # Por defecto, todo el día para el grupo
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    working_group = relationship("DBWorkingGroup", back_populates="group_schedules")


# Tabla: notifications
class DBNotification(Base):
    __tablename__ = "notifications"
    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )  # Usamos BigInteger para IDs potencialmente grandes
    working_group_id = Column(
        Integer, ForeignKey("working_groups.id"), nullable=False
    )  # Notificación asociada a un grupo

    raw_notification = Column(
        String, nullable=False
    )  # La notificación completa tal cual se recibe
    name = Column(String(255), nullable=False)  # Nombre extraído
    amount = Column(Float, nullable=False)  # Monto extraído
    security_code = Column(String(255), nullable=False)  # Código de seguridad extraído

    # Estado de la notificación: received (por Kotlin), sent (por MQTT)
    status = Column(
        Enum(NotificationStatus), default=NotificationStatus.RECEIVED, nullable=False
    )
    notification_timestamp = Column(
        DateTime, nullable=False
    )  # Fecha y hora de detección en Kotlin
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )  # Fecha de registro en el backend

    # Relaciones
    working_group = relationship("DBWorkingGroup", back_populates="notifications")
    # Relación inversa para saber qué device_users_notifications están vinculadas a esta notificación
    device_user_notifications = relationship(
        "DBDeviceUserNotification", back_populates="notification"
    )


# Tabla: device_users_notifications (para evitar notificaciones duplicadas)
class DBDeviceUserNotification(Base):
    __tablename__ = "device_users_notifications"
    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )  # BigInteger para IDs

    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # Usuario al que se le iba a enviar la notificación

    is_active = Column(
        Boolean, default=True, nullable=False
    )  # ¿Por qué `is_active` aquí? Podría ser `is_sent` o `sent_at`
    sent_at = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )  # Cuando se intentó enviar esta notificación a este user/device

    # Relaciones
    notification = relationship(
        "DBNotification", back_populates="device_user_notifications"
    )
    device = relationship("DBDevice", back_populates="device_notifications")
    user = relationship("DBUser", back_populates="user_notifications")

    # Aseguramos que solo haya un registro por (notification, device, user)
    # Esto es crucial para evitar duplicados.
    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "device_id",
            "user_id",
            name="_notification_device_user_uc",
        ),
    )
