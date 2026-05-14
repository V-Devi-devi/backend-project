from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(gt=17, lt=150)
    email: EmailStr
    city: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
    city: Optional[str]

    #class Config:
    #    orm_mode = True

    model_config = {
        "from_attributes": True
    }