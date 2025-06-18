from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List  # Asegúrate de que List esté importado
from app.database import get_db
from app.models import (
    DBUser,
    UserRole,
    DBWorkingGroup,
    DBDeviceUser,
    DBDevice,
)  # Importa DBDeviceUser y DBDevice
from app.schemas import TokenData
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token"
)  # Actualiza la URL a tu nuevo endpoint de login


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# Función para crear el token JWT, ahora incluyendo el ID del grupo y el nombre
def create_access_token(
    user_obj: DBUser, db: Session, expires_delta: Optional[timedelta] = None
):
    to_encode = {
        "sub": user_obj.username,
        "id": user_obj.id,  # Incluir ID del usuario en el token
        "role": user_obj.role.value,
        "working_group_id": None,
        "group_name": None,
    }

    # Lógica para determinar el working_group_id y group_name para el token
    # Asumimos que un usuario 'admin' es el creador de un grupo.
    # Para los miembros, tomaremos el primer grupo al que están asociados vía device_users.

    # Obtener el grupo principal para el usuario en el token
    working_group_id = None
    group_name = None

    if user_obj.role == UserRole.ADMIN:
        # Si es ADMIN, busca el grupo que creó
        group = (
            db.query(DBWorkingGroup)
            .filter(DBWorkingGroup.creator_id == user_obj.id)
            .first()
        )
        if group:
            working_group_id = group.id
            group_name = group.name
    else:  # Si es MEMBER
        # Busca el primer grupo al que está asociado a través de un dispositivo
        # Cargar eagermente las relaciones para evitar problemas de sesión cerrada
        device_user_association = (
            db.query(DBDeviceUser)
            .filter(DBDeviceUser.user_id == user_obj.id)
            .join(DBDeviceUser.device)
            .first()
        )

        if (
            device_user_association
            and device_user_association.device
            and device_user_association.device.working_group
        ):
            working_group_id = device_user_association.device.working_group.id
            group_name = device_user_association.device.working_group.name

    to_encode["working_group_id"] = working_group_id
    to_encode["group_name"] = group_name

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# Función para obtener el usuario actual y sus datos de grupo del token
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        user_id: int = payload.get("id")  # Obtener ID del usuario
        user_role: str = payload.get("role")
        working_group_id: Optional[int] = payload.get("working_group_id")
        group_name: Optional[str] = payload.get("group_name")

        if username is None or user_id is None or user_role is None:
            raise credentials_exception
        token_data = TokenData(
            username=username,
            role=UserRole(user_role),
            working_group_id=working_group_id,
            group_name=group_name,
        )
    except JWTError:
        raise credentials_exception

    # Recuperar el usuario de la DB para asegurar que sigue existiendo y sus datos son válidos
    user = (
        db.query(DBUser)
        .filter(DBUser.id == user_id, DBUser.username == token_data.username)
        .first()
    )
    if user is None or user.is_active is False:
        raise credentials_exception  # Usuario no encontrado o inactivo

    # Para asegurar que las relaciones del usuario (ej. created_working_groups, user_devices)
    # estén cargadas y disponibles para las funciones de dependencia de rol,
    # podemos usar .options(joinedload(...)) o cargar explícitamente.
    # Por simplicidad, asumimos que para las comprobaciones de rol subsiguientes,
    # se volverá a consultar o las relaciones básicas ya están accesibles.

    return user


# Funciones de utilidad para verificar roles y pertenencia a grupo
def get_current_admin(current_user: DBUser = Depends(get_current_user)):
    # Un "admin" es un usuario con UserRole.ADMIN
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador.",
        )

    # Asegurarse de que el admin realmente ha creado un grupo
    if not current_user.created_working_groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El administrador no tiene un grupo de trabajo asociado.",
        )

    return current_user


def get_current_active_user_in_group(current_user: DBUser = Depends(get_current_user)):
    # Este se puede usar para cualquier usuario logueado en un grupo (admin o miembro)
    # Su working_group_id se obtiene del token via get_current_user
    # La pertenencia real al grupo se debería verificar si el usuario es `creator_id` de un grupo,
    # o si está en la tabla `device_users` para un `working_group_id` específico.

    # Para el ADMIN, ya se validó en get_current_admin.
    # Para el MEMBER, necesitamos asegurar que está asociado a un grupo.
    if current_user.role == UserRole.MEMBER:
        # Verificar si tiene al menos una asociación device_user
        if not current_user.user_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no está asociado a un grupo de trabajo.",
            )

    return current_user
