from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    app_name: str = "StreamD"
    debug: bool = False
    db_user: str = "not configured" # db not setup yet
    db_password: str = "not configured"
    db_name: str = "not configured"

config = Config()