from pydantic import BaseModel, ConfigDict, Field

class AnswerBase(BaseModel):
    answer: str = Field(max_length = 1000)

class QuestionBase(BaseModel):
    question: str = Field(max_length = 1000)

class AnswerResponse(AnswerBase):
    pass

