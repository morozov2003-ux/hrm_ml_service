from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional

# --- Схемы пользователя ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    cash_credits: float
    bonus_credits: float

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Схемы биллинга ---
class PromoActivate(BaseModel):
    code: str

class TopUp(BaseModel):
    amount: float

# --- Схемы ML-модели ---
class HRMInput(BaseModel):
    temperatures: List[float]
    fluorescence: List[float]

class TaskResponse(BaseModel):
    task_id: str
    status: str

class PredictionResult(BaseModel):
    task_id: str
    status: str
    genotype: Optional[str] = None
    confidence: Optional[float] = None
    tm: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None
    error: Optional[str] = None