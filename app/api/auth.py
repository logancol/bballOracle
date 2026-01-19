from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta
import logging 
from psycopg import AsyncConnection
from app.models.token import Token
from app.models.user import UserCreate
from app.services.auth_service import authenticate_user, create_access_token
from app.services.user_service import create_user
from app.db.db import get_async_conn_rw, get_async_conn_ar
from app.rate_limiting import limiter

router = APIRouter(prefix='/auth', tags=['Auth'])

log = logging.getLogger(__name__)

# general auth flow from https://www.youtube.com/watch?v=I11jbMOCY0c&t=843s
# added use of pydantic models for input/output 

@router.post("/login")
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], conn: AsyncConnection = Depends(get_async_conn_ar)) -> Token:
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
@limiter.limit("10/minute")
async def register_user(request: Request, new_user: UserCreate, conn: AsyncConnection = Depends(get_async_conn_rw)):
    user_public = await create_user(user=new_user, conn=conn)
    if not user_public:
        raise HTTPException(
            status_code=401,
            detail="Problem registering user."
        )
    return user_public