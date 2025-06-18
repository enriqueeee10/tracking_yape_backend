from sqlalchemy.orm import Session
from app.models import DBUser, UserRole, DBWorkingGroup, DBDeviceUser
from app.schemas import UserCreateOwner, UserCreateMember, UserOut, UserUpdate
from app.repositories.user_repository import UserRepository
from app.repositories.working_group_repository import WorkingGroupRepository
from app.auth import get_password_hash, verify_password
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime


class UserService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.group_repo = WorkingGroupRepository(db)
        self.db = db

    def register_owner(self, user_data: UserCreateOwner) -> UserOut:
        # Verificar si el usuario ya existe
        existing_user = self.user_repo.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está registrado.",
            )

        # Verificar si el nombre de negocio/grupo ya existe
        existing_group = self.group_repo.get_working_group_by_name(user_data.group_name)
        if existing_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del grupo de trabajo ya está en uso.",
            )

        hashed_password = get_password_hash(user_data.password)

        # Crear el grupo de trabajo primero
        new_group = DBWorkingGroup(
            name=user_data.group_name,
            description=f"Grupo de trabajo de {user_data.username}",  # Descripción por defecto
            creator_id=0,  # Temporal, se actualizará después de crear el usuario
        )
        self.db.add(new_group)
        self.db.flush()  # Para obtener el ID del grupo antes de commitear

        # Crear el usuario dueño (admin del grupo)
        new_user = DBUser(
            username=user_data.username,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,  # Asignar rol de ADMIN
            dni=user_data.dni,
            name=user_data.name,
            maternal_surname=user_data.maternal_surname,
            paternal_surname=user_data.paternal_surname,
            is_verified=user_data.is_verified,
            avatar=user_data.avatar,
            email=user_data.email,
            phone=user_data.phone,
            country_code=user_data.country_code,
            is_active=user_data.is_active,
            last_login=datetime.utcnow(),  # Establecer el primer login
        )
        self.user_repo.create_user(new_user)  # Esto también hace commit y refresh

        # Actualizar el creator_id en el grupo de trabajo con el ID del usuario recién creado
        new_group.creator_id = new_user.id
        self.db.commit()  # Un commit final para asegurar la relación circular
        self.db.refresh(
            new_group
        )  # Refrescar para tener el grupo actualizado en el objeto del usuario
        self.db.refresh(
            new_user
        )  # Refrescar al usuario para que cargue la relación created_working_groups

        return UserOut.model_validate(new_user)

    def create_member(
        self, member_data: UserCreateMember, admin_user: DBUser
    ) -> UserOut:
        # Solo el admin de un grupo puede crear miembros para SU grupo
        if admin_user.role != UserRole.ADMIN or not admin_user.created_working_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores de un grupo pueden crear miembros.",
            )

        # Verificar que el nombre de usuario no exista
        existing_user = self.user_repo.get_user_by_username(member_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está registrado.",
            )

        # Verificar que el working_group_id exista y sea el del admin
        target_group = self.group_repo.get_working_group_by_id(
            member_data.working_group_id
        )
        if not target_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )
        if target_group.creator_id != admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para añadir miembros a este grupo.",
            )

        hashed_password = get_password_hash(member_data.password)

        new_member = DBUser(
            username=member_data.username,
            hashed_password=hashed_password,
            role=UserRole.MEMBER,  # Asignar rol de MEMBER
            dni=member_data.dni,
            name=member_data.name,
            maternal_surname=member_data.maternal_surname,
            paternal_surname=member_data.paternal_surname,
            is_verified=member_data.is_verified,
            avatar=member_data.avatar,
            email=member_data.email,
            phone=member_data.phone,
            country_code=member_data.country_code,
            is_active=member_data.is_active,
        )
        self.user_repo.create_user(new_member)

        # Asociar el nuevo miembro al grupo a través de la tabla device_users (sin dispositivo por ahora)
        # Esto es un placeholder. La asociación real de un miembro a un grupo
        # se haría al asignarle un dispositivo o al unirse a un grupo.
        # Para que aparezca en "my-members", necesitamos asociarlo de alguna manera.
        # Podríamos tener una tabla `group_members` en lugar de solo `device_users` para usuarios sin un dispositivo específico.
        # Por ahora, si un miembro no tiene un device_user, no aparecerá en el "miembros del grupo" directamente.
        # Para simplificar y que aparezca, vamos a asumir que al crear un miembro, lo asociamos a un grupo.
        # Nota: La tabla `device_users` es para "usuario de un dispositivo". Si un miembro está en un grupo
        # pero no tiene un dispositivo asociado, la relación `DBWorkingGroup.members` (via `DBDeviceUser`)
        # no lo capturaría automáticamente.
        # Si un "cajero" es simplemente un usuario que trabaja en el grupo, y no necesariamente tiene un dispositivo
        # propio para recibir notificaciones (solo ve el dashboard), entonces DBDeviceUser no es el lugar.
        # Deberíamos crear una tabla de asociación directa `group_members` (user_id, group_id).
        # Sin embargo, siguiendo el ERD, `device_users` parece ser la tabla de unión principal.
        # Por ahora, simplemente lo creamos como usuario y el admin lo vinculará a un dispositivo luego.

        # Retornamos el usuario creado. Su pertenencia al grupo se gestionará al asignarle un dispositivo.
        return UserOut.model_validate(new_member)

    def authenticate_user(self, username: str, password: str) -> Optional[DBUser]:
        user = self.user_repo.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        # Actualizar last_login
        user.last_login = datetime.utcnow()
        self.user_repo.update_user(user)  # Persiste el cambio de last_login
        return user

    def get_user_profile(self, user_id: int) -> Optional[UserOut]:
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return None
        return UserOut.model_validate(user)

    def get_group_members(self, admin_user: DBUser) -> List[UserOut]:
        if admin_user.role != UserRole.ADMIN or not admin_user.created_working_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores de un grupo pueden ver sus miembros.",
            )

        admin_group_id = admin_user.created_working_groups[
            0
        ].id  # Asumimos que el admin tiene un grupo principal

        # Obtener todos los usuarios (miembros y admin) asociados a este grupo a través de device_users
        members_db = (
            self.db.query(DBUser)
            .join(DBDeviceUser)
            .join(DBDeviceUser.device)
            .filter(DBDeviceUser.device.has(working_group_id=admin_group_id))
            .distinct()
            .all()
        )

        # Asegurarse de incluir al propio admin si no está en device_users (ej. si no tiene un dispositivo asociado)
        if admin_user not in members_db:
            members_db.insert(0, admin_user)  # Añadir el admin al principio

        return [UserOut.model_validate(member) for member in members_db]

    def update_user_profile(
        self, user_id: int, user_data: UserUpdate
    ) -> Optional[UserOut]:
        user_to_update = self.user_repo.get_user_by_id(user_id)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
            )

        update_data = user_data.model_dump(exclude_unset=True)

        # Manejar la actualización de la contraseña si se proporciona
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for key, value in update_data.items():
            setattr(user_to_update, key, value)

        self.user_repo.update_user(user_to_update)
        return UserOut.model_validate(user_to_update)

    def deactivate_user(self, user_id: int) -> UserOut:
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
            )
        user.is_active = False
        self.user_repo.update_user(user)
        return UserOut.model_validate(user)
