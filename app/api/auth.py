from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta
import logging 
from psycopg import AsyncConnection
from app.models.token import Token
from app.models.user import UserCreate, UserInDB, UserPublic
from app.services.auth_service import authenticate_user, create_access_token
from app.services.user_service import create_user
from app.db.db import get_async_conn

router = APIRouter(prefix='/auth', tags=['Auth'])

log = logging.getLogger(__name__)

# general auth flow from https://www.youtube.com/watch?v=I11jbMOCY0c&t=843s
# added use of pydantic models for input/output 

@router.post("/login")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], conn: AsyncConnection = Depends(get_async_conn)) -> Token:
    user = await authenticate_user(email=form_data.username, password=form_data.password, conn=conn)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer", expires_in=1440 * 60)
    
@router.post("/register")
async def register_user(new_user: UserCreate, conn: AsyncConnection = Depends(get_async_conn)):
    user_public = await create_user(user=new_user, conn=conn)
    if not user_public:
        raise HTTPException(
            status_code=401,
            detail="Problem registering user."
        )
    return user_public