import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import YapeTransactionBase, YapeTransactionInDB
from app.models import DBYapeTransaction, DBUser, UserRole, DBBusiness
from app.auth import get_current_active_user_in_business
from app.services.websocket_manager import manager  # Importa el manager de WebSockets

router = APIRouter()


@router.post("/yape-notification", response_model=YapeTransactionInDB)
async def receive_yape_notification(
    transaction: YapeTransactionBase,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(
        get_current_active_user_in_business
    ),  # Ahora todos los usuarios autenticados en un negocio pueden enviar
):
    """
    Endpoint para simular la recepción de una notificación de YAPE.
    La transacción se asociará al negocio del usuario que envía la notificación.
    """
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no está asociado a un negocio.",
        )

    db_transaction = DBYapeTransaction(
        amount=transaction.amount,
        sender_name=transaction.sender_name,
        security_code=transaction.security_code,
        user_id=current_user.id,  # Opcional: quien recibió/registró la notif
        business_id=current_user.business_id,  # Asocia la transacción al negocio del usuario
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Notificar SOLO a los clientes conectados que pertenecen al mismo negocio
    await manager.broadcast_to_business(
        db_transaction.business_id,
        json.dumps(YapeTransactionInDB.model_validate(db_transaction).model_dump()),
    )

    return db_transaction


@router.get("/", response_model=List[YapeTransactionInDB])
async def get_all_transactions(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_business),
):
    """
    Obtiene todas las transacciones de Yape para el negocio del usuario actual.
    """
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no está asociado a un negocio.",
        )

    transactions = (
        db.query(DBYapeTransaction)
        .filter(DBYapeTransaction.business_id == current_user.business_id)
        .order_by(DBYapeTransaction.timestamp.desc())
        .all()
    )

    return transactions
