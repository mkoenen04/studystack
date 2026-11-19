# *** NEW ***
from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field, model_validator


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


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    # Trims spaces so "  Math  " and "Math" are the same course
    model_config = {"str_strip_whitespace": True}


class CourseResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    estimated_hours: float = Field(gt=0, le=100)

    model_config = {"str_strip_whitespace": True}


class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    due_date: date
    estimated_hours: float
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# *** NEW ***
class AvailabilityCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def end_must_be_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time.")
        return self


# *** NEW ***
class AvailabilityResponse(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}