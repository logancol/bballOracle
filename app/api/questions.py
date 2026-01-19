from fastapi import APIRouter, Depends, Request
from app.db.db import get_async_conn_ro
from psycopg import AsyncConnection
from app.services.oracle import Oracle
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
import logging
from app.models.reqres import QuestionBase, AnswerBase
from app.rate_limiting import limiter

router = APIRouter()

log = logging.getLogger(__name__)

@router.post("/question", response_model=AnswerBase)
@limiter.limit("10/minute")
async def get_answer(question: QuestionBase, request: Request, conn: AsyncConnection = Depends(get_async_conn_ro), 
                     current_user: UserInDB = Depends(get_current_active_user)) -> AnswerBase:
    log.info(f"====== QUESTION ENDPOINT HIT BY {current_user.email}, QUESTION: {question} ======")
    oracle = Oracle(logger=log, schema=request.app.state.schema, client=request.app.state.openai_client)
    textual_answer = await oracle.ask_oracle(question.question, conn=conn)
    return AnswerBase(answer=textual_answer)