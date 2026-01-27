from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date, time as dt_time
from decimal import Decimal

# ============= Auth Schemas =============
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ============= User Schemas =============
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = Field(..., pattern="^(admin|manager|staff)$")
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserWithDepartment(UserResponse):
    department_name: Optional[str] = None

# ============= Department Schemas =============
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= Customer Schemas =============
class CustomerBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    platform: Optional[str] = None

class CustomerCreate(CustomerBase):
    zalo_id: Optional[str] = None
    meta_id: Optional[str] = None
    telegram_id: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    zalo_id: Optional[str] = None
    meta_id: Optional[str] = None
    telegram_id: Optional[str] = None
    city: Optional[str] = None
    total_orders: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= Keyword Schemas =============
class KeywordBase(BaseModel):
    keyword: str
    department_id: int
    priority: int = 1
    is_active: bool = True

class KeywordCreate(KeywordBase):
    pass

class KeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class KeywordResponse(KeywordBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class KeywordWithDepartment(KeywordResponse):
    department_name: str

# ============= KPI Schemas =============
class KPIBase(BaseModel):
    user_id: int
    metric_name: str
    target_value: Optional[Decimal] = None
    current_value: Decimal = Decimal(0)
    period_start: Optional[date] = None
    period_end: Optional[date] = None

class KPICreate(KPIBase):
    pass

class KPIUpdate(BaseModel):
    metric_name: Optional[str] = None
    target_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None

class KPIResponse(KPIBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= Shift Schemas =============
class ShiftBase(BaseModel):
    name: str
    start_time: dt_time
    end_time: dt_time
    department_id: int

class ShiftCreate(ShiftBase):
    pass

class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[dt_time] = None
    end_time: Optional[dt_time] = None

class ShiftResponse(ShiftBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= UserShift Schemas =============
class UserShiftBase(BaseModel):
    user_id: int
    shift_id: int
    date: date
    status: str = "scheduled"

class UserShiftCreate(UserShiftBase):
    pass

class UserShiftUpdate(BaseModel):
    status: Optional[str] = None

class UserShiftResponse(UserShiftBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= Message Schemas =============
class MessageBase(BaseModel):
    customer_id: int
    content: str
    platform: str
    direction: str = "incoming"
    status: str = "pending"

class MessageCreate(BaseModel):
    customer_id: int
    content: str
    platform: str
    external_id: Optional[str] = None

class MessageUpdate(BaseModel):
    status: Optional[str] = None

class MessageResponse(MessageBase):
    id: int
    external_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageWithCustomer(MessageResponse):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

# ============= MessageAssignment Schemas =============
class MessageAssignmentBase(BaseModel):
    message_id: int
    assigned_to: int
    notes: Optional[str] = None

class MessageAssignmentCreate(MessageAssignmentBase):
    assigned_by: Optional[int] = None
    match_score: Optional[Decimal] = None

class MessageAssignmentUpdate(BaseModel):
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

class MessageAssignmentResponse(MessageAssignmentBase):
    id: int
    assigned_by: Optional[int] = None
    assigned_at: datetime
    completed_at: Optional[datetime] = None
    match_score: Optional[Decimal] = None
    
    class Config:
        from_attributes = True

# ============= Request Schemas =============
class RequestBase(BaseModel):
    type: str = Field(..., pattern="^(leave|salary_increase|transfer|other)$")
    title: str
    description: Optional[str] = None

class RequestCreate(RequestBase):
    pass

class RequestUpdate(BaseModel):
    status: Optional[str] = None
    review_notes: Optional[str] = None

class RequestResponse(RequestBase):
    id: int
    user_id: int
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class RequestWithUser(RequestResponse):
    user_name: str
    reviewer_name: Optional[str] = None

# ============= Notification Schemas =============
class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"
    link: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= Statistics Schemas =============
class StatisticsByDepartment(BaseModel):
    department_id: int
    department_name: str
    total_messages: int
    completed_messages: int
    pending_messages: int
    total_staff: int

class StatisticsByUser(BaseModel):
    user_id: int
    user_name: str
    role: str
    department_name: Optional[str] = None
    total_messages: int
    completed_messages: int
    avg_completion_time: Optional[float] = None

class StatisticsByRequestType(BaseModel):
    request_type: str
    total_requests: int
    approved_requests: int
    rejected_requests: int
    pending_requests: int

class DashboardStatistics(BaseModel):
    total_messages: int
    pending_messages: int
    completed_messages: int
    total_users: int
    total_departments: int
    total_requests: int
    pending_requests: int

# ============= Webhook Schemas =============
class ZaloWebhookMessage(BaseModel):
    event_name: str
    message_id: str
    user_id: str
    message: str
    timestamp: int

class MetaWebhookMessage(BaseModel):
    object: str
    entry: List[dict]
