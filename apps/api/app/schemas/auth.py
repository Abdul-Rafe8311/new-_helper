import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="Asia/Karachi", max_length=64)
    city: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    timezone: str
    city: str | None
    onboarding_completed: bool
