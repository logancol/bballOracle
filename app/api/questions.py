from fastapi import APIRouter, Depends, HTTPException, Request
from app.db.db import get_async_conn
from psycopg import AsyncConnection
from app.services.oracle import Oracle
from app.services.auth_service import get_current_active_user
from app.core.config import settings
from app.models.user import UserInDB
import logging
from app.models.reqres import QuestionBase, AnswerBase

router = APIRouter()

log = logging.getLogger(__name__)

@router.post("/question", response_model=AnswerBase)
async def get_answer(question: QuestionBase, request: Request, conn: AsyncConnection = Depends(get_async_conn), 
                     current_user: UserInDB = Depends(get_current_active_user)) -> AnswerBase:
    log.info(f"====== QUESTION ENDPOINT HIT BY {current_user.email}, QUESTION: {question} ======")
    oracle = Oracle(logger=log, schema=request.app.state.schema, client=request.app.state.openai_client)
    textual_answer = await oracle.ask_oracle(question, conn=conn)
    return AnswerBase(answer=textual_answer)