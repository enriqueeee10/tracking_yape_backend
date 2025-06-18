from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserCreateOwner, UserCreateCashier, UserOut, Token
from app.models import DBUser, DBBusiness, UserRole
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_owner,
    get_current_active_user_in_business,
)

router = APIRouter()


@router.post("/register-owner", response_model=UserOut)
async def register_owner(user_data: UserCreateOwner, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario como dueño y crea un negocio asociado.
    Solo el primer usuario dueño puede registrarse de esta forma.
    """
    # Verificar si ya existe un dueño (simplificación para el ejemplo)
    # En un sistema multi-dueño, esta lógica cambiaría
    # existing_owner = db.query(DBUser).filter(DBUser.role == UserRole.OWNER).first()
    # if existing_owner:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un dueño registrado. Solo se permite un dueño por sistema.")

    db_user = db.query(DBUser).filter(DBUser.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado",
        )

    hashed_password = get_password_hash(user_data.password)

    # Crear el negocio primero
    new_business = DBBusiness(name=user_data.business_name)
    db.add(new_business)
    db.flush()  # Para obtener el ID del negocio antes de commitear

    # Crear el usuario dueño y vincularlo al negocio
    new_user = DBUser(
        username=user_data.username,
        hashed_password=hashed_password,
        role=UserRole.OWNER,
        business_id=new_business.id,  # Asignar el ID del negocio al dueño
    )
    db.add(new_user)
    db.flush()  # Para obtener el ID del usuario dueño

    # Actualizar el owner_id en el negocio
    new_business.owner_id = new_user.id
    db.commit()
    db.refresh(new_user)
    db.refresh(
        new_business
    )  # Opcional, para refrescar el objeto de negocio si es necesario

    return new_user


@router.post("/create-cashier", response_model=UserOut)
async def create_cashier(
    user_data: UserCreateCashier,
    db: Session = Depends(get_db),
    current_owner: DBUser = Depends(
        get_current_owner
    ),  # Solo dueños pueden crear cajeros
):
    """
    Permite a un usuario dueño crear una nueva cuenta de cajero y vincularla a su negocio.
    """
    db_user = db.query(DBUser).filter(DBUser.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado",
        )

    hashed_password = get_password_hash(user_data.password)

    # El cajero se vincula al mismo negocio que el dueño que lo crea
    new_cashier = DBUser(
        username=user_data.username,
        hashed_password=hashed_password,
        role=UserRole.CASHIER,
        business_id=current_owner.business_id,  # Vincula al cajero al negocio del dueño
    )
    db.add(new_cashier)
    db.commit()
    db.refresh(new_cashier)
    return new_cashier


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role.value,
            "business_id": user.business_id,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me/", response_model=UserOut)
async def read_users_me(
    current_user: DBUser = Depends(get_current_active_user_in_business),
):
    return current_user


@router.get("/my-cashiers", response_model=List[UserOut])
async def get_my_cashiers(
    db: Session = Depends(get_db), current_owner: DBUser = Depends(get_current_owner)
):
    """
    Permite al dueño obtener una lista de los cajeros asociados a su negocio.
    """
    cashiers = (
        db.query(DBUser)
        .filter(
            DBUser.business_id == current_owner.business_id,
            DBUser.role == UserRole.CASHIER,
        )
        .all()
    )
    return cashiers
