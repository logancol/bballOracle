import psycopg
from psycopg import AsyncConnection
from fastapi import HTTPException
from typing import Optional
from app.core.config import settings
from bcrypt import hashpw, gensalt, checkpw
from app.models.user import UserCreate, UserPublic, UserInDB

DB_URL = settings.DATABASE_URL

def init_db(conn: psycopg.connection):
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(256),
                password_hash VARCHAR(256) NOT NULL,
                email VARCHAR(256) UNIQUE,
                created_at TIMESTAMP DEFAULT now()
            );
            """)

async def get_user_by_email(conn: AsyncConnection, email: str) -> Optional[UserInDB]:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT email, full_name, password_hash FROM users WHERE email = %s", 
            (email,)
        )
        row = await cur.fetchone()

    if not row:
        return None
    
    user_dict = {
        "email": row[0],
        "full_name": row[1],
        "password_hash": row[2]
    }
    return UserInDB.model_validate(user_dict)

async def create_user(conn: AsyncConnection, user: UserCreate) -> UserPublic:
    password_hash = get_password_hash(user.password)
    try:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO users (full_name, password_hash, email) VALUES (%s, %s, %s)",
                    (user.full_name, password_hash, user.email)
                )
    except psycopg.errors.UniqueViolation as e:
        raise HTTPException(status_code=409, detail="Email already being used.")
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail="DB Error when creating user.") from e
    return UserPublic.model_validate(
        {"email": user.email, "full_name": user.full_name}
    )

def get_password_hash(password: str):
    return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")