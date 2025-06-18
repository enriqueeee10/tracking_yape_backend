import collections
from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    # Diccionario para almacenar conexiones por business_id
    # { business_id: [websocket1, websocket2, ...] }
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = collections.defaultdict(
            list
        )

    async def connect(self, websocket: WebSocket, business_id: int):
        await websocket.accept()
        self.active_connections[business_id].append(websocket)
        print(f"WebSocket conectado para Business ID {business_id}: {websocket.client}")

    def disconnect(self, websocket: WebSocket, business_id: int):
        if business_id in self.active_connections:
            self.active_connections[business_id].remove(websocket)
            if not self.active_connections[
                business_id
            ]:  # Si la lista está vacía, la eliminamos
                del self.active_connections[business_id]
        print(
            f"WebSocket desconectado para Business ID {business_id}: {websocket.client}"
        )

    async def broadcast_to_business(self, business_id: int, message: str):
        if business_id in self.active_connections:
            for connection in self.active_connections[business_id]:
                try:
                    await connection.send_text(message)
                except RuntimeError as e:
                    # Posible error si la conexión se cierra justo antes de enviar
                    print(f"Error al enviar a WebSocket (posiblemente cerrado): {e}")
                    # Podrías querer eliminar la conexión aquí si el error indica que está rota
            print(f"Mensaje broadcast a Business ID {business_id}: {message}")
        else:
            print(f"No hay conexiones activas para Business ID {business_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()
