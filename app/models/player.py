from pydantic import BaseModel

class PlayerCreate(BaseModel):
    name: str
    id: int
    # etc

class PlayerRead(BaseModel):
    name: str
    id: int