from datetime import datetime

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


# *** NEW ***
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


# *** NEW ***
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"