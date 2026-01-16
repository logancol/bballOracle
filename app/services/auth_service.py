from app.core.config import settings
from typing import Annotated, Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends
from app.db.db import get_async_conn
from psycopg import AsyncConnection
from app.models.token import TokenData
from app.models.user import UserCreate, UserInDB, UserPublic
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from app.services.user_service import get_user_by_email
from app.utils.auth_utils import verify_password

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# user authentication returns model containing email, password, and password hash
async def authenticate_user(password: str, email: str, conn: AsyncConnection) -> Optional[UserInDB]:
    if not email or not password:
        return None
    user = await get_user_by_email(conn=conn, email=email)
    if not user:
        return None
    if not verify_password(plain_text=password, hashed_password=user.password_hash):
        return None
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], conn: AsyncConnection = Depends(get_async_conn)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code = 401,
        detail="Could not validate user credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = await get_user_by_email(conn=conn, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    return current_user