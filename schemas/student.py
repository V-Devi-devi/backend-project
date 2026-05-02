from pydantic import BaseModel, Field
from typing import Optional

class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(gt=0, lt=150)
    email: str
    city: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
    city: Optional[str]

    class Config:
        orm_mode = True