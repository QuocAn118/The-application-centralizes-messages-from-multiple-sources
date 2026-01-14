from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, date

from database import get_db
from auth import get_admin_user, get_password_hash
from models import User, Department, Keyword, Message, MessageAssignment, Request, KPI
from schemas import (
    UserResponse, UserCreate, UserUpdate, UserWithDepartment,
    DashboardStatistics, StatisticsByDepartment, StatisticsByUser, StatisticsByRequestType,
    KeywordWithDepartment
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ============= Dashboard & Statistics =============
@router.get("/dashboard", response_model=DashboardStatistics)
async def get_dashboard_statistics(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy thống kê tổng quan cho dashboard Admin"""
    
    total_messages = db.query(func.count(Message.id)).scalar()
    pending_messages = db.query(func.count(Message.id)).filter(Message.status == "pending").scalar()
    completed_messages = db.query(func.count(Message.id)).filter(Message.status == "completed").scalar()
    total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_departments = db.query(func.count(Department.id)).scalar()
    total_requests = db.query(func.count(Request.id)).scalar()
    pending_requests = db.query(func.count(Request.id)).filter(Request.status == "pending").scalar()
    
    return {
        "total_messages": total_messages or 0,
        "pending_messages": pending_messages or 0,
        "completed_messages": completed_messages or 0,
        "total_users": total_users or 0,
        "total_departments": total_departments or 0,
        "total_requests": total_requests or 0,
        "pending_requests": pending_requests or 0
    }

@router.get("/statistics/by-department", response_model=List[StatisticsByDepartment])
async def get_statistics_by_department(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Thống kê theo phòng ban"""
    
    departments = db.query(Department).all()
    result = []
    
    for dept in departments:
        # Đếm tin nhắn
        message_query = db.query(Message).join(MessageAssignment).join(User).filter(
            User.department_id == dept.id
        )
        
        if start_date:
            message_query = message_query.filter(Message.created_at >= start_date)
        if end_date:
            message_query = message_query.filter(Message.created_at <= end_date)
        
        total_messages = message_query.count()
        completed_messages = message_query.filter(Message.status == "completed").count()
        pending_messages = message_query.filter(Message.status == "pending").count()
        
        # Đếm nhân viên
        total_staff = db.query(func.count(User.id)).filter(
            User.department_id == dept.id,
            User.role == "staff",
            User.is_active == True
        ).scalar()
        
        result.append({
            "department_id": dept.id,
            "department_name": dept.name,
            "total_messages": total_messages,
            "completed_messages": completed_messages,
            "pending_messages": pending_messages,
            "total_staff": total_staff or 0
        })
    
    return result

@router.get("/statistics/by-user", response_model=List[StatisticsByUser])
async def get_statistics_by_user(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    department_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Thống kê theo nhân viên"""
    
    user_query = db.query(User).filter(User.is_active == True)
    
    if department_id:
        user_query = user_query.filter(User.department_id == department_id)
    
    users = user_query.all()
    result = []
    
    for user in users:
        # Đếm tin nhắn
        message_query = db.query(Message).join(MessageAssignment).filter(
            MessageAssignment.assigned_to == user.id
        )
        
        if start_date:
            message_query = message_query.filter(Message.created_at >= start_date)
        if end_date:
            message_query = message_query.filter(Message.created_at <= end_date)
        
        total_messages = message_query.count()
        completed_messages = message_query.filter(Message.status == "completed").count()
        
        # Tính thời gian xử lý trung bình
        avg_time_query = db.query(
            func.avg(
                func.extract('epoch', MessageAssignment.completed_at - MessageAssignment.assigned_at)
            )
        ).filter(
            MessageAssignment.assigned_to == user.id,
            MessageAssignment.completed_at.isnot(None)
        )
        
        if start_date:
            avg_time_query = avg_time_query.filter(MessageAssignment.assigned_at >= start_date)
        if end_date:
            avg_time_query = avg_time_query.filter(MessageAssignment.assigned_at <= end_date)
        
        avg_completion_time = avg_time_query.scalar()
        
        result.append({
            "user_id": user.id,
            "user_name": user.full_name,
            "role": user.role,
            "department_name": user.department.name if user.department else None,
            "total_messages": total_messages,
            "completed_messages": completed_messages,
            "avg_completion_time": float(avg_completion_time) if avg_completion_time else None
        })
    
    return result

@router.get("/statistics/by-request-type", response_model=List[StatisticsByRequestType])
async def get_statistics_by_request_type(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Thống kê theo loại yêu cầu"""
    
    request_types = ["leave", "salary_increase", "transfer", "other"]
    result = []
    
    for req_type in request_types:
        query = db.query(Request).filter(Request.type == req_type)
        
        if start_date:
            query = query.filter(Request.created_at >= start_date)
        if end_date:
            query = query.filter(Request.created_at <= end_date)
        
        total_requests = query.count()
        approved_requests = query.filter(Request.status == "approved").count()
        rejected_requests = query.filter(Request.status == "rejected").count()
        pending_requests = query.filter(Request.status == "pending").count()
        
        result.append({
            "request_type": req_type,
            "total_requests": total_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "pending_requests": pending_requests
        })
    
    return result

# ============= Keywords Management =============
@router.get("/keywords", response_model=List[KeywordWithDepartment])
async def get_all_keywords(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Xem tất cả từ khóa trong hệ thống"""
    
    keywords = db.query(Keyword).offset(skip).limit(limit).all()
    
    result = []
    for kw in keywords:
        result.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "department_id": kw.department_id,
            "priority": kw.priority,
            "is_active": kw.is_active,
            "created_at": kw.created_at,
            "department_name": kw.department.name if kw.department else None
        })
    
    return result

# ============= User Management =============
@router.get("/users", response_model=List[UserWithDepartment])
async def get_all_users(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    role: Optional[str] = None,
    department_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
):
    """Lấy danh sách tất cả người dùng"""
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if department_id:
        query = query.filter(User.department_id == department_id)
    
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "department_id": user.department_id,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "department_name": user.department.name if user.department else None
        })
    
    return result

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Tạo người dùng mới"""
    
    # Kiểm tra email đã tồn tại
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng"
        )
    
    # Tạo user mới
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        department_id=user_data.department_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin người dùng"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Cập nhật các trường
    if user_data.email:
        # Kiểm tra email mới có bị trùng không
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được sử dụng"
            )
        user.email = user_data.email
    
    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.department_id is not None:
        user.department_id = user_data.department_id
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Xóa người dùng (soft delete - set is_active = False)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Không cho phép xóa chính mình
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa tài khoản của chính mình"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "Đã xóa người dùng thành công"}

@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: str = Query(..., regex="^(admin|manager|staff)$"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Thay đổi vai trò của người dùng"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Không cho phép thay đổi role của chính mình
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể thay đổi vai trò của chính mình"
        )
    
    old_role = user.role
    user.role = new_role
    db.commit()
    
    return {
        "message": f"Đã thay đổi vai trò từ {old_role} sang {new_role}",
        "user_id": user_id,
        "old_role": old_role,
        "new_role": new_role
    }

# ============= Departments =============
@router.get("/departments", response_model=List[dict])
async def get_all_departments(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tất cả phòng ban"""
    
    departments = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "description": d.description} for d in departments]
