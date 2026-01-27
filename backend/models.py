from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date, Time, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    users = relationship("User", back_populates="department")
    keywords = relationship("Keyword", back_populates="department", cascade="all, delete-orphan")
    shifts = relationship("Shift", back_populates="department", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager', 'staff')", name="check_user_role"),
    )
    
    department = relationship("Department", back_populates="users")
    kpis = relationship("KPI", back_populates="user", cascade="all, delete-orphan")
    user_shifts = relationship("UserShift", back_populates="user", cascade="all, delete-orphan")
    requests = relationship("Request", foreign_keys="Request.user_id", back_populates="user")
    reviewed_requests = relationship("Request", foreign_keys="Request.reviewed_by", back_populates="reviewer")
    message_assignments = relationship("MessageAssignment", foreign_keys="MessageAssignment.assigned_to", back_populates="assignee")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))
    zalo_id = Column(String(255))
    meta_id = Column(String(255))
    telegram_id = Column(String(255))
    platform = Column(String(50))
    city = Column(String(100))
    total_orders = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    messages = relationship("Message", back_populates="customer", cascade="all, delete-orphan")

class Keyword(Base):
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"))
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    department = relationship("Department", back_populates="keywords")

class KPI(Base):
    __tablename__ = "kpis"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    metric_name = Column(String(255), nullable=False)
    target_value = Column(DECIMAL(10, 2))
    current_value = Column(DECIMAL(10, 2), default=0)
    period_start = Column(Date)
    period_end = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="kpis")

class Shift(Base):
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    department = relationship("Department", back_populates="shifts")
    user_shifts = relationship("UserShift", back_populates="shift", cascade="all, delete-orphan")

class UserShift(Base):
    __tablename__ = "user_shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')", name="check_user_shift_status"),
    )
    
    user = relationship("User", back_populates="user_shifts")
    shift = relationship("Shift", back_populates="user_shifts")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    external_id = Column(String(255))
    direction = Column(String(20), default="incoming")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("direction IN ('incoming', 'outgoing')", name="check_message_direction"),
        CheckConstraint("status IN ('pending', 'assigned', 'in_progress', 'completed')", name="check_message_status"),
    )
    
    customer = relationship("Customer", back_populates="messages")
    assignments = relationship("MessageAssignment", back_populates="message", cascade="all, delete-orphan")

class MessageAssignment(Base):
    __tablename__ = "message_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"))
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    notes = Column(Text)
    match_score = Column(DECIMAL(5, 2))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    message = relationship("Message", back_populates="assignments")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="message_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

class Request(Base):
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="pending")
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("type IN ('leave', 'salary_increase', 'transfer', 'other')", name="check_request_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_request_status"),
    )
    
    user = relationship("User", foreign_keys=[user_id], back_populates="requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_requests")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")
    is_read = Column(Boolean, default=False, index=True)
    link = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="notifications")
