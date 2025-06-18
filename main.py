from typing import Optional
import uvicorn
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    Query,
)
from app.routers import (
    auth_router,
    working_groups_router,
    devices_router,
    notifications_router,
    schedules_router,
)
from app.services.websocket_manager import manager
from app.core.config import settings
from app.auth import (
    get_current_user,
)  # Solo necesitas get_current_user para el WebSocket
from jose import JWTError, jwt
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import DBUser  # Para obtener el tipo de usuario desde get_current_user

app = FastAPI(title=settings.PROJECT_NAME)

# Incluir los nuevos routers
app.include_router(auth_router.router)
app.include_router(working_groups_router.router)
app.include_router(devices_router.router)
app.include_router(notifications_router.router)
app.include_router(schedules_router.router)


# Ruta raíz
@app.get("/")
async def read_root():
    return {"message": "Bienvenido al Backend de Tracking YAPE"}


# Endpoint WebSocket
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # El token se pasa como query parameter para el WebSocket
    token: str = Query(..., description="Token de autenticación JWT para el WebSocket"),
    db: Session = Depends(
        get_db
    ),  # Inyectar la dependencia de la DB para get_current_user
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales del WebSocket",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Validar el token y obtener el usuario (reutilizando get_current_user)
        # Necesitamos pasar el token directamente, no a través de Depends(oauth2_scheme) en la firma del websocket
        # Así que replicamos la lógica de decodificación y validación de get_current_user aquí.
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        working_group_id: Optional[int] = payload.get("working_group_id")
        # group_name: Optional[str] = payload.get("group_name") # No es estrictamente necesario en el WebSocket

        if (
            username is None
            or user_id is None
            or user_role is None
            or working_group_id is None
        ):
            raise credentials_exception

        # Opcional: Revalidar el usuario contra la base de datos si se requiere mayor seguridad
        user = (
            db.query(DBUser)
            .filter(DBUser.id == user_id, DBUser.username == username)
            .first()
        )
        if user is None or user.is_active is False:
            raise credentials_exception

    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"Error al decodificar/validar token JWT en WebSocket: {e}")
        raise credentials_exception

    # Conecta el WebSocket y asocia el working_group_id
    # Ahora el manager usa working_group_id para agrupar conexiones
    await manager.connect(websocket, working_group_id)
    try:
        while True:
            # Mantener la conexión abierta, si el cliente envía algo, puedes manejarlo aquí
            # Por ejemplo, un "ping" o un mensaje de confirmación
            data = await websocket.receive_text()
            # Opcional: procesar mensajes del cliente si es necesario
            # await manager.send_personal_message(f"Recibido: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(
            websocket, working_group_id
        )  # Desconecta y remueve del working_group_id
        print(f"WebSocket desconectado para Business ID {working_group_id}.")
    except Exception as e:
        print(f"Error inesperado en WebSocket para Business ID {working_group_id}: {e}")
        manager.disconnect(websocket, working_group_id)
