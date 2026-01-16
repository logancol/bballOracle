from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Union

class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_token: str
    token_type: str = "bearer"
    expires_in: Union[int, None] # *seconds* or none

class TokenData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr