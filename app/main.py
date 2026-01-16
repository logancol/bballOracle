from openai import OpenAI
from app.core.config import settings
import logging
import sys
from contextlib import asynccontextmanager
from app.db.db import get_async_pool, get_pool
from app.api.questions import router as questions_router
from app.api.auth import router as auth_router
from fastapi import FastAPI

# Global logging config for api
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] "
           "[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):

    OPENAI_API_KEY = settings.OPENAI_API_KEY
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set or not loaded")
    
    # instantiating openai client as part of global state
    app.state.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    schema_path = settings.SCHEMA_PATH
    try: # loading the db schema from file one time to avoid doing it repetitivly
        with open(schema_path, 'r') as file:
            app.state.schema = file.read()
    except FileNotFoundError:
        logger.error(f"====== Schema file not found: {schema_path} ======")
        return
    get_pool().open()
    await get_async_pool().open() # open sync and async connection pools
    try:
        yield
    finally:
        await get_async_pool().close() # close sync and async connection pools end of life
        get_pool().close()
app = FastAPI(lifespan=lifespan, title="BBALL ORACLE")

# Stream handler for uvicorn console
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

app.include_router(questions_router)
app.include_router(auth_router)