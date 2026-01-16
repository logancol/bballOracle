from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, ValidationError
from typing import Union
import re


# base user model validates that email is an expected shape, full name optional
# in all contexts a user must be identified by email
class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_validator(cls, v: str):
        if not re.search(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v):
            raise ValidationError("Invalid email")
        return v
        
    full_name: Union[str, None]

# accepts password and validates
class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str: # setting up in case I want to change password validation requirements
        if len(v) < 8:
            raise ValidationError("Password should be at least 8 characters")
        if not re.search(r"[^\w\s]", v):
            raise ValidationError("Password must contain a special character")
        return v

# explicit definition of what we want to make public to users, which would just be their email and optionally full name
class UserPublic(UserBase):
    model_config = ConfigDict(extra="forbid")

# never expose
class UserInDB(UserBase):
    model_config = ConfigDict(extra="forbid")
    password_hash: str