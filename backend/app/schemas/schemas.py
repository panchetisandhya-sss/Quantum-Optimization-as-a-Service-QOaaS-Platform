from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, EmailStr

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class GoogleSSOInput(BaseModel):
    email: EmailStr
    credential: Optional[str] = None
    prompt_mode: Optional[str] = "select_account"

# Optimization Job Schemas
class OptimizationJobCreate(BaseModel):
    service_type: str  # "portfolio" or "staffing"
    input_data: Dict[str, Any]

class OptimizationJobOut(BaseModel):
    id: str
    user_id: str
    service_type: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    ai_explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Audit Log Schemas
class AuditLogOut(BaseModel):
    id: int
    action: str
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Contribution Schemas
class ContributionCreate(BaseModel):
    name: str
    email: EmailStr
    institution: Optional[str] = None
    github: Optional[str] = None
    title: str
    category: str
    description: str
    markdown_content: Optional[str] = None
    code_content: Optional[str] = None
    file_path: Optional[str] = None

class ContributionReview(BaseModel):
    status: str  # APPROVED, REJECTED

class ContributionOut(BaseModel):
    id: str
    name: str
    email: str
    institution: Optional[str] = None
    github: Optional[str] = None
    title: str
    category: str
    description: str
    markdown_content: Optional[str] = None
    code_content: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

