from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "manager"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    telegram_id: int | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginForm(BaseModel):
    email: str
    password: str
