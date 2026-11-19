# *** NEW ***
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserResponse(BaseModel):
    # The response never includes the password or its hash
    id: int
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# *** NEW ***
class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    # Trims spaces so "  Math  " and "Math" are the same course
    model_config = {"str_strip_whitespace": True}


# *** NEW ***
class CourseResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# *** NEW ***
class AssignmentCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    estimated_hours: float = Field(gt=0, le=100)

    model_config = {"str_strip_whitespace": True}


# *** NEW ***
class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    due_date: date
    estimated_hours: float
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}